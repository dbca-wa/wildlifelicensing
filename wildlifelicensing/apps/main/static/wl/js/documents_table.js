define(['jQuery', 'lodash', 'js/wl.dataTable'], function($, _, dataTable) {
    return {
        initDocumentsTable: function(tableSelector, data, editURL,deleteURL) {
            dataTable.initTable($(tableSelector), {
                paging: false,
            }, [
                {title: 'Name', data: 'name', render: $.fn.dataTable.render.text()},
                {title: 'Description', data: 'description', render: $.fn.dataTable.render.text()},
                {title: 'File', data: 'file', render: $.fn.dataTable.render.text()},
                {title: 'Uploaded Date', data: 'uploaded_date'},
                {title: 'Action', data: 'id', render: function(data, type, row) {
                	return '<a href="' + editURL + _.escape(data) + '">Edit</a> &nbsp;&nbsp;<a href="' + deleteURL + _.escape(data) + '">Delete</a>';
                }}
            ]).populate(data);
        }
    }
});
