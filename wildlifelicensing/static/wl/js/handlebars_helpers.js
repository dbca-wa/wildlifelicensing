define(['handlebars.runtime'], function(Handlebars) {
    Handlebars.registerHelper('isEqual', function(lvalue, rvalue, options) {
        if (arguments.length < 3)
            throw new Error("Handlebars Helper equal needs 2 parameters");
        if(lvalue != rvalue ) {
            return options.inverse(this);
        } else {
            return options.fn(this);
        }
    });

    Handlebars.registerHelper('getURLFilename', function(url) {
        // Document URLs carry the original file name as "#filename=<encoded name>" (Task 19098)
        var marker = '#filename=',
            markerIndex = url.indexOf(marker);
        if (markerIndex !== -1) {
            return decodeURIComponent(url.substr(markerIndex + marker.length));
        }
        return url.substr(url.lastIndexOf('/') + 1);
    });
});
