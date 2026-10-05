define(['jQuery', 'lodash', 'js/wl.dataTable'], function($, _, dataTable) {
    return {
        initProfilesTable: function(tableSelector, data, editURL) {
            dataTable.initTable($(tableSelector), {
                paging: false,
            }, [
                {title: 'Display Name', data: 'name', render: $.fn.dataTable.render.text()},
                {title: 'Email', data: 'email', render: $.fn.dataTable.render.text()},
                /*
                {title: 'Auth Identity', data: 'auth_identity',render:function(data,type,row) {
                    if (data) {
                        return '<span class="fa fa-check" aria-hidden="true"></span'
                    } else {
                        return '<span class="fa fa-times" aria-hidden="true"></span'
                    }
                }},
                */
                {title: 'Institution', data: 'institution', render: $.fn.dataTable.render.text()},
                {title: 'Postal Address', data: 'postal_address.search_text', render: $.fn.dataTable.render.text()},
                {title: 'Action', data: 'id', render: function(data, type, row) {
                	return '<a href="' + editURL + _.escape(data) + '">Edit</a>';
                }}
            ]).populate(data);
        }
    }
});
