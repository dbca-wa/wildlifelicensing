define(["jquery", "select2", "bootstrap-datetimepicker"], function ($) {
  "use strict";

  return {
    init: function () {
      var $searchCustomer = $("#searchCustomer");
      var $selectButton = $("#select");

      $searchCustomer.select2({
        theme: "bootstrap-5",
        width: "100%",
        placeholder: "Search for a customer...",
        allowClear: true,
        minimumInputLength: 2,
        ajax: {
          url: "/search_customers",
          dataType: "json",
          delay: 250, // Replaced quietMillis with delay
          data: function (params) {
            // Use params.term for version 4.0.x
            return {
              q: params.term,
            };
          },
          processResults: function (data) {
            // Replaced results with processResults
            return {
              results: data,
            };
          },
          cache: true,
        },
      });

      // Handle button state based on selection
      $searchCustomer.on("change", function (e) {
        var val = $(this).val();
        $selectButton.prop("disabled", !val);
      });

      // Initialize datetimepicker if element exists
      if ($("#id_dob").length) {
        $("#id_dob").datetimepicker({
          format: "DD/MM/YYYY",
        });
      }
    },
  };
});
