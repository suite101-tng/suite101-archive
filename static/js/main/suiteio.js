//suiteio
define([
    'jquery',
    'backbone',
    'underscore',
    'velocity',
    'velocity-ui',       
    'bootstrap/bootstrap'//noexports
],
function(
    jQuery,
    Backbone,
    _
) {
    'use strict';
    //export suiteio namespace
    var $ = jQuery;
    var vent = _.extend({}, Backbone.Events);
    var suiteio = {
        initialize: _initialize,
        setupCSRF: setupCSRF,
        isIE: ((navigator.appName === 'Microsoft Internet Explorer') || ((navigator.appName === 'Netscape') && (new RegExp("Trident/.*rv:([0-9]{1,}[.0-9]{0,})").exec(navigator.userAgent) !== null))),
        convertImgToBase64: convertImgToBase64,
        parseQueryString: parseQueryString,
        throbber: '<div class="orbitalloader blue"><span class="suite-icon spinning"></span></div>',
        throbberAlt: '<div class="orbitalloader blue"><i class="io io-load-c io-spin"></i></div>',
        vent: vent
    };

    function parseQueryString (queryString){
        var params = {};
        if(queryString){
            _.each(
                _.map(decodeURI(queryString).split(/&|\?/g),function(el,i){
                    var aux = el.split('='), o = {};
                    if(aux.length >= 1){
                        var val = undefined;
                        if(aux.length == 2)
                            val = aux[1];
                        if(aux[0])
                            o[aux[0]] = val;
                    }
                    return o;
                }),
                function(o){
                    _.extend(params,o);
                }
            );
        }
        return params;
    };

    function convertImgToBase64 (url, callback, width, outputFormat){
        var canvas = document.createElement('CANVAS'),
            ctx = canvas.getContext('2d'),
            img = new Image(),
            _width = width || 1280;
        img.crossOrigin = 'Anonymous';
        img.onload = function(){
            var neww = (img.width >= _width)? _width : img.width, // don't make the base64 version bigger than the actual image
                newh = Math.round((img.height / img.width) * neww);
            canvas.height = newh;
            canvas.width = neww;
            ctx.drawImage(img,0,0,neww,newh);
            var dataURL = canvas.toDataURL(outputFormat || 'image/png');
            callback.call(this, dataURL);
            // Clean up
            canvas = null;
        };
        img.src = url;
    };

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    function sameOrigin(url) {
        // test that a given url is a same-origin URL
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
        (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
        // or any other URL that isn't scheme relative or absolute i.e relative.
        !(/^(\/\/|http:|https:).*/.test(url));
    }

    function setupCSRF(csrf) {
        var oldSync = Backbone.sync;
        Backbone.sync = function(method, model, options) {
            options.beforeSend = function(xhr){
                xhr.setRequestHeader('X-CSRFToken', csrf);
            };
            return oldSync(method, model, options);
        };
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
                    // Send the token to same-origin, relative URLs only.
                    // Send the token only if the method warrants CSRF protection
                    // Using the CSRFToken value acquired earlier
                    xhr.setRequestHeader('X-CSRFToken', csrf);
                }
            }
        });
        suiteio.csrf = csrf;
    }
    
    function _initialize(options) {
        //*** Libraries setup ***
        //**csrf token
        var csrf;
        if(options && options.csrf_token) {
            csrf = options.csrf_token;
        } else {
            csrf = $('meta[name="csrftoken"]').attr('content');
        }
        if(csrf) {
            setupCSRF(csrf);
        }
        //**Backbone Views extensions
        Backbone.View = Backbone.View.extend({
            events: {
                'click.actionBouncer [data-actionbind]': 'actionBouncer'
            },
            actionBouncer: function actionBouncer(e) {
                var $ctarget = $(e.currentTarget),
                    targetData = $ctarget.data(),
                    action = targetData.action;
                if(targetData.keepDefault === undefined) {
                    e.preventDefault();
                }
                if(action && this[action] && typeof this[action] === 'function') {
                    if(targetData.continuePropagate === undefined){
                        e.stopPropagation();
                    }
                    this[action].call(this, e);
                    return true;
                }
            },
            destroy: function() {
                this.trigger('destroy');
                this.stopListening();
                this.undelegateEvents();
            }
        });
        // TODO: allow json objects to be stored directly with $.cookie api 
        // https://github.com/js-cookie/js-cookie
    }
    _.extend(suiteio, Backbone.Events);
    return suiteio;
});