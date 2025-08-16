document.addEventListener('DOMContentLoaded', function(){
  const f = document.querySelector('form');
  if (!f) return;
  f.addEventListener('submit', function(){
    const btn = f.querySelector('button');
    if(btn){ btn.disabled = true; btn.textContent = 'Signing in…'; }
  });
});



