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
    var LoginView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'submit #pwResetForm': 'resetPassword',
                'focus #pwResetForm input': 'clearFormError',
                'click .showReset': 'showReset',
                'hide.bs.modal': 'exit',


                'submit .loginForm': 'submitForm',
                'click .authError': 'clearErrors',


                'keyup .loginPassword': 'passwordKeyup'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            if(options && options.join) {
                this.startWithJoinTab = true;
            } else {
                this.startWithJoinTab = false;
            }
            if(options.el) {
                this.setElement(options.el);
            }

            this.authUrl = options.authUrl || '/login'

            this.loginMode = options.loginMode || 'login';
            this.nextUrl = window.location.pathname;
            this.pleaseLoginTmplPromise = suiteio.templateLoader.getTemplate('please-login-modal');
        },
      
        render: function() {
            var self = this;
            var disabled = suiteio.logDis;  

            this.pleaseLoginTmplPromise.done(function(tmpl) {
                var $loginModal = $(tmpl({
                    csrf: suiteio.csrf,
                    disabled: disabled,
                    join: self.startWithJoinTab
                }));
                $loginModal.modal({blur: true});

                self.setElement($loginModal);
                self.$('input, textarea').placeholder();
            });
        },

        loadLogin: function(e) {
            var self = this;
            var duration = 140;
            var $button = this.$('.loginButton');
            this.$('.loginRegBlurb').addClass('active').siblings().removeClass('active');
            this.clearErrors();
            if(this.loginMode == 'forgot' || this.loginMode == 'forgotThanks') {
                if(this.loginMode == 'forgotThanks') {
                    this.$('.loginForm').velocity('transition.fadeIn', 140);   
                    this.$('.resetThanks').remove();         
                }                
                this.$('.socialOptions').velocity('transition.fadeIn', duration).addClass('active');
                this.$('.resetBlurb').velocity('transition.fadeOut', duration).removeClass('active rel');
            }
            this.$('.regExtras').addClass('active').velocity('stop', true).velocity({ minHeight: 0, height: 0 }, { 
                duration: duration
            });
            this.$('.firstPass').addClass('active').show().velocity('stop', true).velocity({ minHeight: 46, height: 46 }, { 
                duration: duration
            });            

            $button.html('Sign in');
            var wait = setTimeout(function() { 
                self.$('.loginFoot').addClass('active').velocity({ opacity: 1 }, { duration: duration });
                self.$('.regFoot').velocity({ opacity: 0 }, { duration: duration });                
                self.$('.resetFoot').velocity({ opacity: 0 }, { duration: duration }).removeClass('active');
                self.$('.regExtras').removeClass('active');
                self.$('.regFoot').removeClass('active');
             }, (duration));
            this.loginMode = 'login';            
        },

        loadReg: function(e) {
            var self = this;
            var duration = 140;
            var $button = this.$('.loginButton');
            this.clearErrors();
            this.$('.regExtras').addClass('active').velocity('stop', true).velocity({ minHeight: 46, height: 46, display: 'block' }, { 
                duration: duration
            });

            $button.html('Create an account');
            var wait = setTimeout(function() { 
                this.$('.regExtras').addClass('open');
                self.$('.regFoot').addClass('active').velocity({ opacity: 1 }, { duration: duration });
                self.$('.loginFoot').velocity({ opacity: 0 }, { duration: duration });                
                self.$('.loginFoot').removeClass('active');
             }, (duration));
            this.loginMode = 'reg';
        },

        loadForgotThanks: function(e) {
            console.log('load forgot thanks!');
            var self = this;
            var duration = 140;
            var $button = this.$('.loginButton');
            var $resetThanks = '<div class="reg-mode active centered reset-thanks resetThanks">We\'ve just sent you an email. Follow the instructions to reset your password.</div>'

            this.$('.resetBlurb').removeClass('active').before($resetThanks);
            this.$('.forgotBlurb').removeClass('active');
            
            this.$('.loginForm').velocity('transition.fadeOut', 140);            
            this.loginMode = 'forgotThanks';
        },  

        loadReset: function(e) {
            console.log('load reset!');
            var self = this;
            var duration = 140;
            var $button = this.$('.loginButton');
            this.$('.forgotBlurb').addClass('active').siblings().removeClass('active');
            this.clearErrors();
            this.$('.firstPass').velocity('stop', true).velocity({ minHeight: 0, height: 0 }, { 
                duration: duration
            });
            this.$('.socialOptions').velocity({ opacity: 0 }, { duration: duration });
            this.$('.resetBlurb').addClass('active').velocity('transition.fadeIn', duration);

            $button.html('Request a reset');
            var wait = setTimeout(function() { 
                self.$('.firstPass').removeClass('active');
                self.$('.resetFoot').addClass('active').velocity({ opacity: 1 }, { duration: duration });
                self.$('.loginFoot').velocity({ opacity: 0 }, { duration: duration });                
                self.$('.loginFoot').removeClass('active');
             }, (duration));
            this.loginMode = 'forgot';
        },        

        clearErrors: function() {
            var $authError = this.$('.authError')
            $authError.velocity('transition.fadeOut', 140);            
            var wait = setTimeout(function() { 
                $authError.html('');
            }, 140);
        },

        submitForm: function(e) {
            var self = this;
            var duration = 140;
            e.preventDefault();
            var $button = $('.loginButton');
            var $authError = this.$('.authError');
            var loginMode = this.loginMode || 'login';
            $button.dynamicButton({immediateEnable: true});
            switch(loginMode) {
                case 'login':
                    console.log('submitting login');
                break;
                case 'reg':
                    console.log('submitting reg');
                break;
                case 'forgot':
                    console.log('submitting reset');
                break;
            }

            var $loginErrorBlock = this.$('.authErrorBlock');
            var formfields = this.$('.loginForm').find('input');
            var formData = {};
            if(formfields && formfields.length) {
                for(var i=0, l=formfields.length, item ; i<l ; ++i) {
                    var field = formfields[i];
                    formData[field.name] = $(field).val();
                }
            } else {
                // no form fields?!
            }    

            // override the form field in case we've switched tabs
            formData['authtype'] = this.loginMode;

            $.ajax({
                url: this.authUrl,
                type: 'POST',
                data: formData,
                success: function(response) {
                    $button && $button.dynamicButton('revert');
                    if(response.error) {
                        $authError.html(response.error);
                        $authError.velocity('transition.fadeIn', duration);
                    } else {
                        switch(self.loginMode) {
                            case 'forgot':
                                self.loadForgotThanks();
                            break;
                            case 'login':
                                window.location.reload();
                            break;
                        }
                    }
                }
            });

        },

        passwordKeyup: function(e) {
            var rawString = $(e.currentTarget).text(); 
            console.log(rawString);           
            console.log(rawString.length);

            var code = e.charCode || e.keyCode || e.which;
            var valid;
            if(code === 27) {
                // this.resetSlugField();
            }
            if(code === 13) {
                console.log('enter!');
                e.preventDefault();
            }
            // this.validateGaCode(string)
        },

        submitLoginRegForm: function(formData, url) {
            var self = this;
            var $submit = $.ajax({
                url: url,
                type: 'POST',
                data: formData
            });
            return $submit
        },

        clearFormError: function(errorType) {
            this.$('.formError').html('');
        },

        renderFormError: function(errorType) {
            switch (errorType) {
                case 'nonMatching':
                    var msg = 'Passwords do not match';
                break;
                case 'emptyForm':
                    var msg = 'Oh, you have to enter <em>something</em>...';
                break;
                case 'missingSecond':
                    var msg = 'Please enter your new password again';
                break;
                default:
                break;
            }
            this.$('.formError').html('<div class="inner-error innerError">' + msg + '</div>');
        },

        resetPassword: function(e) {
            console.log('trying to reset the password');
            e.preventDefault();
            var $form = $(e.currentTarget),
                postData = $form.serialize(),
                $action = $form.attr('action'),
                $unlocked = false,
                p1 = $('#password').val(),
                p2 = $('#password2').val();
                console.log(p1);
                
            if(!p1 && !p2) {
                console.log('sorry the form looks empty to me');
                this.renderFormError('emptyForm');
                return;
            }
            if(postData && !p2) {
                console.log('you have to enter it again!');
                this.renderFormError('missingSecond');
                return;
            }
            if(p1 != p2) {
                console.log('passwords do not match!');
                this.renderFormError('nonMatching');
                return;
            }

            return $.ajax({
                url: $action,
                dataType: 'json',
                type: 'POST',
                data: postData,
                success: function() {
                    suiteio.notify.alert({
                        msg: 'done!',
                        type: 'success'
                    });
                    window.location = '/';
                    // suiteio.fireLoginModal();
                },
                error: function() {
                    self.formErrorHandler.apply(self, arguments);
                }
            })

        },

        // $('.logIn').on('click', function(e) {
        //     e.preventDefault();
        //     var url = $(e.currentTarget).attr('href');
        //     var currentUrl = window.location.pathname;
        //     window.location = url + '?next=' + currentUrl;
        // });


        showReset: function(e) {
            e.preventDefault();
                this.$('.showReg').removeClass('active');
                this.$('.showLogin').removeClass('active');
        },

        exit: function() {
            this.trigger('closeLoginModal');
        },

        destroy: function() {
            Backbone.View.prototype.destroy.apply(this, arguments);
            this.$el.remove();
        }


    });
    return LoginView;
});