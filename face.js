// Face capture: getUserMedia -> canvas -> base64 JPEG -> Flask (OpenCV face detection)
let stream,shot=null;const v=document.getElementById('v'),cv=document.getElementById('c');
const show=(id,on)=>document.getElementById(id).classList.toggle('d-none',!on);
async function startCam(){
  try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false});}
  catch(e){return toast(e.name==='NotFoundError'?'No camera found':'Camera permission denied (HTTPS required)','danger')}
  v.srcObject=stream;await v.play();show('b-cap',true);show('b-start',false)}
function capture(){cv.width=v.videoWidth;cv.height=v.videoHeight;cv.getContext('2d').drawImage(v,0,0);
  shot=cv.toDataURL('image/jpeg',.85);show('v',false);show('c',true);show('b-cap',false);show('b-retake',true);show('b-submit',true)}
function retake(){shot=null;show('v',true);show('c',false);show('b-cap',true);show('b-retake',false);show('b-submit',false)}
async function submitFace(){
  const r=await fetch('/api/mark-face-attendance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image:shot})});
  const d=await r.json();toast(d.message,d.ok?'success':'danger');
  document.getElementById('result').textContent=d.ok?`${d.message} (${d.date} ${d.time})`:d.message;
  if(d.ok){stream.getTracks().forEach(t=>t.stop());show('b-submit',false);show('b-retake',false)}}
