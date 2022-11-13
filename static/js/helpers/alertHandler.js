define(['jquery', 'underscore'], function($, _) {
    'use strict';
    var alertTemplate = '<div class="clearfix alert alert-block alert-<%=type%>" style="display: none;">'+
            '<% if(heading) { %><h4 class="alert-heading"><%= heading %></h4><% } %>'+
            '<p><%= msg %></p>'+
            '<% if(prompt) { %><div class="alert-footer alertFooter centered">'+
            '<% if(yes) { %><button class="btn btn btn-nakedBlue  promptBtn btn-<%= yesClass%> Yes" href="#"><%= yes %></button><% } %> '+
            '<% if(no) { %><button class="btn btn btn-nakedGray promptBtn btn-<%= noClass%> No" href="#"><%= no %></button><% } %></p><% } %>'+
            '<% if(closeButton){ %><div class="alert-footer alertFooter centered"><button class="btn btn btn-nakedBlue promptBtn">Got it!</button></div><% } %>'+
          '</div>';
    var altTmpCmpl = _.template(alertTemplate);
    var alertHandler = {
        initialize: function(args) {
            if(this.initialized) return this;
            this.$parent = $('.alertsContainer');
            this.initialized = true;
            return this;
        },
        prompt: function(_options) {
            if(!this.initialized) this.initialize();
            var defaults = {
                heading: '',
                clickOnClose: false,
                closeButton: false,
                type: 'info',
                msg: '',
                yes: 'Yes',
                yesClass: 'inverse',
                no: 'No',
                showScrim: false,
                noClass: ''
            },
            tmpPrompt, promptDfd,
            options = $.extend(defaults, _options);
            options.prompt = true;
            //fail safe - so we won't have an unclosable prompt if both yes and no are set to false
            options.clickOnClose = !(!!options.yes && !!options.no);
            tmpPrompt = new PromptView(options);
            this.$parent.append(tmpPrompt.render());
            $('body').addClass('alertOpen');
            return tmpPrompt.getPromptDfd();
        },
        alert: function(_options) {
            if(!this.initialized) this.initialize();
            var defaults = {
                heading: '',
                clickOnClose: true,
                closeButton: false,
                type: 'info',
                autoFade: true,
                delay: 2000,
                msg: ''
            },
            tmpAlert,
            options = $.extend(defaults, _options);
            options.prompt = false;
            tmpAlert = new AlertView(options);
            this.$parent.append(tmpAlert.render());
            // $('body').addClass('alertOpen');
            return true;
        }
    };
    var AlertView = function(options) {
        if(options) {
            this.options = options;
            this.$el = $(altTmpCmpl(options));
            this.bind();
        }
    };
    AlertView.prototype.bind = function() {
        var self = this;
        this.$el.on('click', '.close', function(e) {
            e.preventDefault();
            self.close(true);
        });
        if(this.options && this.options.clickOnClose) {
            this.$el.on('click', function(e) {
                e.preventDefault();
                self.close(true);
            });
        }
    };
    AlertView.prototype.close = function(immediate) {
        $('.sharedScrim').hide();
        var delay=100;
        if(immediate) {
            delay=0;
        }
        this.$el.off('.alertHandlerEvents');
            $('body').removeClass('alertOpen');
        this.$el.fadeOut(delay, function() {
            $(this).remove();
        });
    };
    AlertView.prototype.render = function() {
        var _$el = this.$el;
        //     timeout = this.options.delay;
        var timeout = this.options.delay;
        _$el.velocity('stop', true).velocity('transition.expandIn', 250);

        if(this.options && this.options.autoFade && timeout >= 0) {
            setTimeout(function() {
                _$el.velocity('stop', true).velocity('reverse').remove();
            }, timeout);
        }
        return _$el;
    };
    //PromptView extends AlertView
    var PromptView = function(options) {
        if(options) this.options = options;
        var self = this;
        this.$el = $(altTmpCmpl(options));
        this.promptDfd = $.Deferred();
        this.promptDfd.done(function(decision) {
            self.close(true);
        });
        this.bind();
    };
    //setup inheritance
    PromptView.prototype = new AlertView();
    PromptView.constructor = PromptView;
    PromptView.prototype.bind = function() {
        //bind events for buttons
        AlertView.prototype.bind.apply(this, arguments);
        var self = this;
        this.$el.on('click.alertHandlerEvents', '.btn', function(e) {
            e.preventDefault();
            self.$el.off('.alertHandlerEvents');
            var $button = $(e.currentTarget);
            if($button.hasClass('Yes')) {
                self.promptDfd.resolve(true);
            } else if($button.hasClass('No')) {
                self.promptDfd.resolve(false);
            }
        });
        $(document).on('click.alertHandlerEvents keyup.alertHandlerEvents', function(e) {
            var code = e.charCode || e.keyCode || e.which;
            if((e.type === 'keyup' && code === 27) ||
                (!self.$el.has($(e.target)).length && !$(e.target).is(self.$el))
            ) {
                self.$el.off('.alertHandlerEvents');
                $(document).off('.alertHandlerEvents');
                self.promptDfd.resolve(false);
            }
        });
    };
    PromptView.prototype.getPromptDfd = function() {
        return this.promptDfd;
    };
    PromptView.prototype.render = function() {
        if(this.options.showScrim) {
            $('.sharedScrim').show();
        }
        return this.$el.fadeIn();
    };
    return alertHandler;
});