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
    "lodash": "libs/lodash.min",
    "bootstrap.treeView": "libs/bootstrap-treeview.min",
    "datatables.net": "libs/jquery.dataTables.min",
    "datatables.bootstrap": "libs/dataTables.bootstrap5.min",
    "datatables.datetime": "libs/datetime-moment",
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
