require.config({
  baseUrl: "/static/wl",
  paths: {
    "jQuery": "libs/jquery.min",
    // Use the Bootstrap 5 bundle (includes Popper) so JS matches the BS5 markup/CSS
    "bootstrap": "libs/bootstrap.bundle.min",
    "bootstrap-datetimepicker": "libs/bootstrap-datetimepicker.min",
    // Use Select2 v4 full bundle (includes compat modules) to work with RequireJS
    "select2": "libs/select2.full.min",
    "handlebars": "libs/handlebars.amd.min",
    "handlebars.runtime": "libs/handlebars.runtime.amd.min",
    "moment": "libs/moment.min",
    "parsley": "libs/parsley.min",
    "datatables.net": "https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min",
    // DataTables Bootstrap 5 integration
    "datatables.bootstrap": "https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min",
    "lodash": "libs/lodash.min",
    "bootstrap.treeView": "libs/bootstrap-treeview.min",
    "datatables.datetime": "//cdn.datatables.net/plug-ins/1.10.11/sorting/datetime-moment",
  },
  map: {
    "*": {
      jquery: "jQuery",
      datatables: "datatables.net",
    },
  },
  shim: {
    jQuery: {
      exports: "$",
    },
    lodash: {
      exports: "_",
    },
    bootstrap: {
      deps: ["jQuery"],
      exports: "bootstrap",
    },
    "bootstrap-datetimepicker": {
      deps: ["jQuery", "bootstrap", "moment"],
    },
    // select2: {
    //   // Select2 v4 is AMD-aware; only depend on jQuery here.
    //   deps: ["jQuery"],
    // },
    parsley: {
      deps: ["jQuery"],
    },
    "datatables.net": {
      deps: ["jQuery"],
    },
    "datatables.bootstrap": {
      deps: ["jQuery"],
    },
    "bootstrap.treeView": {
      deps: ["bootstrap"],
    },
  },
});
