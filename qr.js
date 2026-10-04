// Student QR scanner (jsQR). Needs HTTPS (or localhost) for camera.
let stream,scanning=false;
async function startScan(){
  const v=document.getElementById('v'),c=document.createElement('canvas'),x=c.getContext('2d');
  try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});}
  catch(e){return toast('Camera permission denied or unavailable','danger')}
  v.srcObject=stream;await v.play();scanning=true;
  (function tick(){
    if(!scanning)return;
    if(v.videoWidth){c.width=v.videoWidth;c.height=v.videoHeight;x.drawImage(v,0,0);
      const r=jsQR(x.getImageData(0,0,c.width,c.height).data,c.width,c.height);
      if(r){scanning=false;stream.getTracks().forEach(t=>t.stop());return send(r.data)}}
    requestAnimationFrame(tick)})();
}
async function send(t){
  const r=await fetch('/api/mark-qr-attendance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:t})});
  const d=await r.json();toast(d.message,d.ok?'success':'danger');
  document.getElementById('result').innerHTML=d.ok?`<b>${d.message}</b><br>Date: ${d.date}<br>Time: ${d.time}<br>ID: ${d.student}<br>Method: ${d.method}`:`<b class="text-danger">${d.message}</b>`;
}
