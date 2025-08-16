document.addEventListener('DOMContentLoaded', () => {
  const links = document.querySelectorAll('.sidebar .nav-link');
  const path = window.location.pathname;
  links.forEach(l => {
    if (l.getAttribute('href') !== '/' && path.startsWith(l.getAttribute('href'))) {
      l.setAttribute('aria-current', 'page');
    }
  });

  // Payroll employee quick info (progressive enhancement)
  const empSelect = document.querySelector('select[name="employee"]');
  const info = document.getElementById('emp-info');
  if (empSelect && info) {
    const render = () => {
      const opt = empSelect.options[empSelect.selectedIndex];
      if (!opt) return;
      info.textContent = opt.textContent;
    };
    empSelect.addEventListener('change', render);
    render();
  }
});

