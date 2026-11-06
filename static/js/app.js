document.addEventListener('DOMContentLoaded',()=>{
  const themeSelect=document.getElementById('themeSelect');
  const key='gromaster-theme';
  const applyTheme=value=>{const dark=value==='dark'||(value==='system'&&window.matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.bsTheme=dark?'dark':'light';};
  if(themeSelect){themeSelect.value=localStorage.getItem(key)||'light';applyTheme(themeSelect.value);themeSelect.addEventListener('change',()=>{localStorage.setItem(key,themeSelect.value);applyTheme(themeSelect.value);});}
  const sidebar=document.getElementById('appSidebar'),toggle=document.getElementById('sidebarToggle'),scrim=document.getElementById('sidebarScrim');
  const close=()=>{sidebar?.classList.remove('open');scrim?.classList.remove('show');};
  toggle?.addEventListener('click',()=>{sidebar?.classList.toggle('open');scrim?.classList.toggle('show');});scrim?.addEventListener('click',close);
  document.querySelectorAll('form:not(.filter-bar)').forEach(form=>{form.addEventListener('submit',()=>{const button=form.querySelector('button[type="submit"],button:not([type])');if(button&&!button.disabled){button.disabled=true;button.innerHTML='<span class="spinner-border spinner-border-sm me-2"></span>Saving…';}});});
  const bulkSearch=document.getElementById('bulkSearch');bulkSearch?.addEventListener('input',()=>{const q=bulkSearch.value.trim().toLowerCase();document.querySelectorAll('#bulkTable tbody tr[data-search]').forEach(row=>{row.hidden=!row.dataset.search.includes(q);});});
});
