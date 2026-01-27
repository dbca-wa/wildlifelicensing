define(['jQuery', 'select2'], function ($) {
    "use strict";

    return {
        init: function() {
            console.log("Customer Search Init: Started"); // Check if init is called

            var $searchCustomer = $('#searchCustomer');
            
            // 1. Check if the element exists
            if ($searchCustomer.length === 0) {
                console.error("Error: #searchCustomer element not found in DOM");
                return;
            }

            // 2. Check if Select2 is loaded correctly
            if (typeof $.fn.select2 === 'undefined') {
                console.error("Error: Select2 library is not loaded or not attached to jQuery");
                return;
            }

            console.log("Initializing Select2 on:", $searchCustomer);

            $searchCustomer.select2({
                theme: 'bootstrap-5',
                width: '100%',
                placeholder: 'Search for a customer...',
                allowClear: true,
                minimumInputLength: 1, // Set to 1 for easier testing
                ajax: {
                    url: '/search_customers',
                    dataType: 'json',
                    delay: 250,
                    data: function (params) {
                        console.log("Ajax triggering: Searching for ->", params.term); // This MUST fire
                        return {
                            q: params.term,
                        };
                    },
                    processResults: function (data) {
                        console.log("Ajax Success: Data received ->", data);
                        return { results: data };
                    },
                    cache: true
                }
            });

            $searchCustomer.on('change', function(e) {
                console.log("Selection changed, Value:", $(this).val());
                $('#select').prop('disabled', !$(this).val());
            });

            console.log("Customer Search Init: Completed");
        }
    }
});