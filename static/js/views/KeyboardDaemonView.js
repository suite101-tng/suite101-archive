define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio'
], function(
    $,
    Backbone,
    _,
    suiteio
) {
    'use strict';
    var KeyboardDaemon = Backbone.View.extend({
        initialize: function(options) {
            if(options) {
                this.baseSearchURL = options.baseSearchURL;
                // this.searchSuitesUrl = options.searchSuitesUrl;
                // this.searchArticlesUrl = options.searchArticlesUrl;
                // this.searchUsersUrl = options.searchUsersUrl;
            }
            this.opened = false;
            this.capturedKeys = '';
            this.rendering = $.Deferred();
            this.allowEveCollapse = true;
            this.resume();
        },
        isSuspended: function() {
            return this.suspended;
        },
        toggle: function() {
            if(this.isSuspended()) {
                this.resume();
            } else {
                this.suspend();
            }
        },
        suspend: function() {
            this.suspended = true;
            this.stopListening(suiteio.keyWatcher);
        },
        resume: function() {
            this.listenToOnce(suiteio.keyWatcher, 'keypress:alphanumeric', function(e) {
                if(e.ctrlKey || e.metaKey || e.altKey) {
                    //if a modifier key is pressed, don't do it
                    return;
                }
                if($(e.target).hasClass('wysiwyg') || $(e.target).attr('contenteditable')) {return;}
                window.setTimeout(suiteio.createNewArticle(null, true), 0);
            });
            this.listenTo(suiteio.keyWatcher, 'keypress:alphanumeric keypress:32', function(e) {
                var code = e.charCode || e.keyCode || e.which;
                if($(e.target).hasClass('wysiwyg')) {return;}
                this.injectKeys(String.fromCharCode(code));
            });
            this.suspended = false;
        },
        getCapturedKeys: function() {
            return this.capturedKeys;
        },
        render: function(capturedKeys, searchTerm) {
            if($('body').hasClass('modal-open')) {
                //if there's another overlay, don't open;
                return;
            }
            //this.trigger('showSearch');
            // var self =this
            //press esc key to exit search screen
            this.listenToOnce(suiteio.keyWatcher, 'keydown:27', this.exit);
            this.opened = true;
            // this.$el.show('drop', {direction: 'down'}, 200, function() {
            //     //no need to listen to alphanumeric key when search screen is open
            //     self.stopListening(suiteio.keyWatcher, 'keypress:alphanumeric');
            //     $input.focus();
            //     $input.val(self.capturedKeys); //firefox requires that we set the val AFTER we focus. ODD.
            //     self.$('.tips').fadeIn();
            //     $('body').addClass('modal-open');
            //     //press enter key to do search
            //     // self.listenTo(suiteio.keyWatcher, 'keydown:13', function() {
            //     //     self.doSearch();
            //     // });

            //     if (searchTerm !== undefined && searchTerm !== '') {
            //         $input.val(searchTerm);
            //     }
            //     self.rendering.resolve(self);
            // });
        },
        resetCapturedKeys: function() {
            this.capturedKeys = '';
        },
        injectKeys: function(key) {
            if(this.capturedKeys.match(/^\s*$/) && key === ' ') {
                return;
            }
            this.capturedKeys += key;
        },
        exit: function(e) {
            if(e && e.type === 'click' && ((e.currentTarget !== e.target) && $(e.currentTarget).data('action') !== 'exit')) {
                return;
            }
            var self = this;
            self.stopListening();
            this.opened = false;
            this.undelegateEvents();
            this.initialize();
            this.delegateEvents();
            $('body').removeClass('modal-open');
        }
    });
    return KeyboardDaemon;
});