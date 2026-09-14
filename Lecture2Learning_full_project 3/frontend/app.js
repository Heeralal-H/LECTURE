let token = localStorage.getItem("l2l_token");
let currentQuiz = null;
let currentReport = null;

const $ = id => document.getElementById(id);

function headers(json=true){
  const h = {};
  if(json) h["Content-Type"] = "application/json";
  if(token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function api(url, options={}){
  options.headers = {...headers(options.body !== undefined), ...(options.headers || {})};
  const res = await fetch(url, options);
  const data = await res.json().catch(()=>({}));
  if(!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function showAuth(mode){
  $("login-form").classList.toggle("hidden", mode !== "login");
  $("register-form").classList.toggle("hidden", mode !== "register");
  document.querySelectorAll(".tab").forEach((x,i)=>x.classList.toggle("active",(mode==="login"?i===0:i===1)));
  $("auth-message").textContent = "";
}

async function login(e){
  e.preventDefault();
  try{
    const data = await api("/api/auth/login",{method:"POST",body:JSON.stringify({
      email:$("login-email").value,password:$("login-password").value
    })});
    token=data.token; localStorage.setItem("l2l_token",token); await startApp();
  }catch(err){$("auth-message").textContent=err.message}
}

async function register(e){
  e.preventDefault();
  try{
    const data = await api("/api/auth/register",{method:"POST",body:JSON.stringify({
      name:$("reg-name").value,email:$("reg-email").value,password:$("reg-password").value
    })});
    token=data.token; localStorage.setItem("l2l_token",token); await startApp();
  }catch(err){$("auth-message").textContent=err.message}
}

async function logout(){
  try{await api("/api/auth/logout",{method:"POST"})}catch(e){}
  token=null; localStorage.removeItem("l2l_token");
  $("auth-view").classList.remove("hidden"); $("app-view").classList.add("hidden");
  $("user-area").innerHTML="";
}

async function startApp(){
  try{
    const me=await api("/api/me");
    $("auth-view").classList.add("hidden"); $("app-view").classList.remove("hidden");
    $("welcome-name").textContent=`Welcome, ${me.name}`;
    $("user-area").innerHTML=`<button class="secondary" onclick="logout()">Logout</button>`;
    await refresh();
  }catch(err){logout()}
}

async function refresh(){
  const [dashboard, lectures]=await Promise.all([api("/api/dashboard"),api("/api/lectures")]);
  $("stats").innerHTML=[
    ["lectures","Lectures Uploaded"],["quizzes","Quizzes Completed"],
    ["average_score","Average Score"],["topics_mastered","Topics Mastered"],
    ["topics_to_revise","Topics to Revise"]
  ].map(([k,label])=>`<div class="stat"><strong>${k==="average_score"?dashboard[k]+"%":dashboard[k]}</strong><span>${label}</span></div>`).join("");
  $("lectures").innerHTML=lectures.length?lectures.map(l=>`
    <div class="lecture">
      <h3>${escapeHtml(l.title)}</h3>
      <div class="tags">${l.topics.map(t=>`<span class="tag">${escapeHtml(t)}</span>`).join("")}</div>
      <div class="actions">
        <button class="primary" onclick="generateQuiz(${l.id})">Generate Quiz</button>
        <button class="secondary" onclick="deleteLecture(${l.id})">Delete</button>
      </div>
    </div>`).join(""):`<p>No lectures yet. Upload your first PDF.</p>`;
  $("attempts").innerHTML=dashboard.recent_attempts.length?dashboard.recent_attempts.map(a=>`
    <div class="attempt">
      <div><strong>Quiz #${a.quiz_id}</strong><small style="display:block;color:#6b7592">${new Date(a.created_at).toLocaleString()}</small></div>
      <div><span class="score">${a.percentage}%</span><br><button class="secondary" onclick="viewReport(${a.id})">Report</button></div>
    </div>`).join(""):`<p>No quiz attempts yet.</p>`;
}

async function uploadPDF(e){
  const file=e.target.files[0]; if(!file) return;
  const form=new FormData(); form.append("file",file);
  try{
    const res=await fetch("/api/lectures/upload",{method:"POST",headers:{"Authorization":`Bearer ${token}`},body:form});
    const data=await res.json(); if(!res.ok) throw new Error(data.detail||"Upload failed");
    toast("Lecture uploaded and topics detected.");
    await refresh();
  }catch(err){toast(err.message)}
  e.target.value="";
}

async function deleteLecture(id){
  if(!confirm("Delete this lecture and its quizzes?")) return;
  try{await api(`/api/lectures/${id}`,{method:"DELETE"}); await refresh(); toast("Lecture deleted.");}
  catch(err){toast(err.message)}
}

async function generateQuiz(id){
  try{
    toast("Generating quiz...");
    const data=await api(`/api/lectures/${id}/generate-quiz`,{method:"POST"});
    currentQuiz=await api(`/api/quizzes/${data.quiz_id}`);
    renderQuiz();
    $("quiz-section").classList.remove("hidden");
    $("quiz-section").scrollIntoView({behavior:"smooth"});
  }catch(err){toast(err.message)}
}

function renderQuiz(){
  $("quiz-title").textContent=currentQuiz.title;
  $("quiz-container").innerHTML=currentQuiz.questions.map((q,i)=>`
    <div class="q">
      <div class="q-meta">Question ${i+1} · ${escapeHtml(q.topic)} · ${q.difficulty}</div>
      <h3>${escapeHtml(q.question_text)}</h3>
      ${q.options.map((o,j)=>`
        <label class="option">
          <input type="radio" name="q-${q.id}" value="${escapeAttr(o)}">
          ${String.fromCharCode(65+j)}. ${escapeHtml(o)}
        </label>`).join("")}
    </div>`).join("");
}

async function submitQuiz(){
  if(!currentQuiz) return;
  const answers=[];
  for(const q of currentQuiz.questions){
    const selected=document.querySelector(`input[name="q-${q.id}"]:checked`);
    if(selected) answers.push({question_id:q.id,answer:selected.value});
  }
  try{
    currentReport=await api(`/api/quizzes/${currentQuiz.id}/submit`,{
      method:"POST",body:JSON.stringify({answers,time_taken:0})
    });
    renderReport(currentReport);
    $("report-section").classList.remove("hidden");
    $("report-section").scrollIntoView({behavior:"smooth"});
    await refresh();
  }catch(err){toast(err.message)}
}

async function viewReport(id){
  try{
    currentReport=await api(`/api/attempts/${id}/report`);
    renderReport(currentReport);
    $("report-section").classList.remove("hidden");
    $("report-section").scrollIntoView({behavior:"smooth"});
  }catch(err){toast(err.message)}
}

function renderReport(r){
  $("report").innerHTML=`
    <div class="report-summary">
      <div><div class="big-score">${r.percentage}%</div><div>${r.score} correct answers</div></div>
      <div>
        <h3>Topic-wise Performance</h3>
        ${r.topic_performance.map(t=>`
          <div class="progress-row">
            <div class="progress-head"><strong>${escapeHtml(t.topic)}</strong><span>${t.percentage}% · <span class="status ${t.status==="Strong"?"strong":t.status==="Good"?"good":"weak"}">${t.status}</span></span></div>
            <div class="progress"><i style="width:${t.percentage}%"></i></div>
          </div>`).join("")}
      </div>
    </div>
    <div class="report-columns">
      <div class="report-box"><h3>✓ Strengths</h3>${r.strengths.length?`<ul>${r.strengths.map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul>`:"<p>Keep practicing to build strong areas.</p>"}</div>
      <div class="report-box"><h3>⚠ Revision Priorities</h3>${r.revision_priorities.length?`<ol>${r.revision_priorities.map(x=>`<li><strong>${escapeHtml(x)}</strong></li>`).join("")}</ol>`:"<p>No urgent weak topics detected.</p>"}</div>
    </div>
    <div class="report-box" style="margin-top:20px"><h3>Personalized Recommendations</h3><ul>${r.recommendations.map(x=>`<li>${escapeHtml(x)}</li>`).join("")}</ul></div>`;
}

function closeQuiz(){$("quiz-section").classList.add("hidden")}
function closeReport(){$("report-section").classList.add("hidden")}
function toast(msg){
  $("toast").textContent=msg; $("toast").classList.add("show");
  setTimeout(()=>$("toast").classList.remove("show"),2500);
}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
function escapeAttr(s){return escapeHtml(s)}
if(token) startApp();
