//utility view implements a Event Dispatcher for global keypress/keydown/keyup keyboard events
//fires <eventtype>:<charcode> events in the form of a backbone event
define(['jquery', 'backbone'], function(
    $,
    Backbone
){
    'use strict';
    var KeyWatcher = Backbone.View.extend({
        el: 'body',
        events: {
            'keyup': 'keyHandler',
            'keydown': 'keyHandler',
            'keypress': 'keyHandler'
        },
        keyHandler: function(e) {
            var code = e.charCode || e.keyCode || e.which,
                chr = String.fromCharCode(code);
            if (chr.match(/[0-9a-z-_#]/ig)) {
                if(this.$el.hasClass('modal-open') || e.target.tagName.match(/input|textarea/ig)) { return; }
                this.trigger(e.type + ':alphanumeric', e);
            }
            this.trigger(e.type  +':'+code, e);
            this.trigger(e.type, e);
        }
    });
    return KeyWatcher;
});