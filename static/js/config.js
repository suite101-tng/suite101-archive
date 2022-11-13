// Project requirejs configuration file
//
// For more options and documentation visit:
// https://github.com/jrburke/r.js/blob/master/build/example.build.js
require.config({
    // Define where dependencies have been installed to so they can be refered
    // to in define() and require() calls by their package name rather than
    // their overly verbose path
    paths   : {
        'jquery'                    : 'lib/jquery-1.12.1.min',
        'velocity'                  : 'lib/velocity.min',
        'velocity-ui'               : 'lib/velocity.ui.min',
        'interact'                  : 'lib/interact',
        'dropzone'                  : 'lib/dropzone',        
        'underscore'                : 'lib/underscore',
        'backbone'                  : 'lib/backbone',
        'lib/handlebars'            : 'lib/handlebars-v4.0.5',
        'handlebars'                : 'lib/handlebars-packaged',
        'bootstrap'                 : 'lib/bootstrap',
        'suiteio'                   : 'main/suiteio',
        'moment'                    : 'lib/moment',
        'taggle'                    : 'lib/taggle',
        'autosize'                  : 'lib/autosize'
    },
    shim : {
        jquery : {
            exports: ['$', 'jQuery']
        },
        underscore: {
            exports: '_'
        },
        backbone : {
            deps: ['underscore', 'jquery'],
            exports: 'Backbone'
        },

        'lib/handlebars': {
            exports: 'Handlebars'
        },
        
        'lib/rangy-core': {
            exports: 'rangy'
        },

        'lib/underwood': {
            exports: 'Underwood'
        },
                
        'lib/Countable': {
            exports: 'Countable'
        },
        
        'velocity': {
            deps: ['jquery']
        },

        'velocity-ui': {
            deps: [ 'velocity' ]
        },

        'interact': {
        },

        'lib/dropzone': {
            deps: []
        },

        'autosize': {
            exports: 'autosize'
        },

        'lib/lazysizes': {
            deps: []
        },

        'lib/bindWithDelay': {
            deps: ['jquery']
        },

        'lib/classList': {
        },
              
        'lib/json2': {
            deps: []
        },

        'helpers/jquery.placeholder': {
            deps: ['jquery']
        },

        'helpers/jquery.dynamicButtonHelper': {
            deps: ['jquery']
        },
        
        'bootstrap/tab': {
            deps: ['jquery']
        },
        
        'bootstrap/tooltip': {
            deps: ['jquery']
        },

        'bootstrap/popover': {
            deps: ['jquery', 'bootstrap/tooltip']
        },
        
        'bootstrap/dropdown': {
            deps: ['jquery']
        },
        
        'bootstrap/modal': {
            deps: ['jquery']
        },
                       
        'lib/highstock': {
            exports: 'Highcharts',
            dep: ['jquery']
        },

        'taggle': {
            exports: 'Taggle'
        },

    }

    // Directory where our optimized files will be compiled to:
    // {{STATIC_URL}}/compiled/js/
    // dir     : "./static/compiled/js/",

});