document.addEventListener('DOMContentLoaded', () => {
  const period = document.getElementById('period_type');
  const amountLabel = document.getElementById('amount_label');
  const workedLabel = document.getElementById('worked_label');
  const update = () => {
    const t = period.value;
    if (t === 'DAILY') { amountLabel.firstChild.textContent = 'Amount per day'; workedLabel.firstChild.textContent = 'Days worked'; }
    else if (t === 'WEEKLY') { amountLabel.firstChild.textContent = 'Amount per week'; workedLabel.firstChild.textContent = 'Weeks worked'; }
    else if (t === 'BIWEEKLY') { amountLabel.firstChild.textContent = 'Amount per period'; workedLabel.firstChild.textContent = 'Periods worked'; }
    else if (t === 'MONTHLY') { amountLabel.firstChild.textContent = 'Amount per month'; workedLabel.firstChild.textContent = 'Months worked'; }
  };
  period?.addEventListener('change', update);
  update();
});

