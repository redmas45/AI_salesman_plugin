(function () {
  var target = window.location.pathname.replace(/\/app\.js$/, "/");
  if (!/\/crm\/?$/.test(target)) target = target.replace(/\/?$/, "/");
  var url = target + "?crm_reload=" + Date.now();
  window.location.replace(url);
})();
