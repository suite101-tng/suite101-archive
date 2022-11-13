define([
    'jquery',
    'backbone',
    'underscore',
    'helpers/searchUsersMixins',
    'models/User',
    'models/SuiteInvite',
    'suiteio'
], function(
    $,
    Backbone,
    _,
    searchUsersMixins,
    User,
    SuiteInvite,
    suiteio
) {
    'use strict';
    var SELECTED = '<span class="selected"><i class="io io-ios-checkmark-empty fa-lg"></i></span>',
        SPINNER = '<i class="io io-load-c io-spin"></i>';
    var InviteToSuiteView = Backbone.View.extend({

        events: function() {
            return _.extend({
                'submit .addPeopleForm': '_formSubmit',
                'keyup .addUsername': _.debounce(this.onSearchUsers, 400),
                'click .userSuggest .userTeaser': 'selectFoundPeople'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            var self = this;
            options = options || {};
            this.suite = options.suite;
            this.emailInviteModalPromise = suiteio.templateLoader.getTemplate('suite-invite-email-modal');
            this.findPeople(true);
            this.templateReady = suiteio.templateLoader.getTemplate('suite-invite-modal');
            this.userTeaserTmplPromise = suiteio.templateLoader.getTemplate('user-teaser-nolink');
            this.mySuiteInvites = new SuiteInvite.collection();
            this.mySuiteInvitesPromise = this.mySuiteInvites.fetch({
                data: {
                    user: suiteio.loggedInUser.id,
                    suite: this.suite.id
                }
            }).done(function() {
                self.render();
            });
        },

        _formSubmit: function(e) {
            if(e) {e.preventDefault();}
            console.log('caught the submitted form');
            this.findPeople();
        },

        getInvitedIds: function() {
            return _(this.mySuiteInvites.toJSON()).chain().pluck('userInvited').pluck('id').value();
        },

        findPeople: function(skipMembers) {
            var q = this.$('.addUsername').val(),
                self = this,
                promises = [],
                responseHandler = function(nresp, mresp) {
                    nresp = nresp || {};
                    // mresp = mresp || {};
                    var neighs = [],
                        // mems = [],
                        all = [];
                    neighs = _.isArray(nresp)? nresp[0].objects : (nresp.objects)? nresp.objects : [];
                    // mems = _.isArray(mresp)? mresp[0].objects : (mresp.objects)? mresp.objects : [];

                    all = _.uniq(neighs, false, function(user) {
                        return user.id
                    });
                    self.renderFoundPeople(all, q);
                    if(all.length) {
                        self.foundPeople = new Backbone.Collection(all);
                    }
                };
            if(q && q.match(/.+@.+\..+/i)) {
                searchUsersMixins.findMembersWithEmail(q).done(function(response) {
                    if(response.objects && response.objects.length) {
                        //found a member with that email
                        responseHandler(response);
                    } else {
                        //calls up modal
                        self._fireEmailInviteModal(q);
                    }
                });
            } else {
                promises.push(searchUsersMixins.findNeighbours(q,'chat',this.chatModel.id));
                if(!skipMembers) {
                    promises.push(searchUsersMixins.findNeighbours(q,'chat',this.chatModel.id));
                }
                $.when.apply(null, promises).done(responseHandler);
            }
        },

        _fireEmailInviteModal: function(email) {
            var self = this;
            this.emailInviteModalPromise.done(function(tmpl) {
                var $modal = $(tmpl({
                    title: 'Invite ' + email + ' to talk',
                    instruction: '',
                    placeholder: 'Hey, thought you might like to join this discussion...'
                }));
                $modal.modal();
                $modal.on('submit', '.inviteForm', function(e) {
                    e.preventDefault();
                    var message = $(this).find('.msg').val(),
                        $submit = $(this).find('.submitBtn').dynamicButton({immediateEnable: true});
                    self.inviteThroughEmail(email, message, $submit, $modal);
                });
            });
        },

        inviteThroughEmail: function(email, message, $submit, $modal) {
            var args = arguments,
                self = this;
            if(!this.chatModel.id && this.chatModel.newonclient) {
                this.chatModel.save().done(function() {
                    self.inviteThroughEmail.apply(self, args);
                });
                return;
            }
            this.chatModel.inviteThroughEmail(email, message).done(function() {
                $submit.dynamicButton('revert');
                $modal.modal('hide');
                self.$('.addUsername').val('');
                suiteio.notify.alert({msg: 'Thank you. An email invite has been sent to ' + email + '.'});
            }).fail(function(response) {
                var msg = 'There has been an error completing your request, please try again later';
                if(response && response.responseJSON && response.responseJSON.chatInvite && response.responseJSON.chatInvite.__all__) {
                    if(response.responseJSON.chatInvite.__all__ === 'Already invited this user') {
                        msg = 'You\'ve already invited ' + email + '.';
                    }
                }
                $submit.dynamicButton('revert');
                suiteio.notify.alert({msg: msg, type: 'error'});
            });
        },

        selectFoundPeople: function(e) {
            var self = this;
            var alreadyInvited;
            e.preventDefault();
            var $currentTarget = $(e.currentTarget),
                userId = $currentTarget.data('id');
            this.mySuiteInvitesPromise.done(function() {
                alreadyInvited = self.mySuiteInvites.find(function(model) {
                    return model.get('userInvited').id === userId
                });
                if(!alreadyInvited) {
                    $currentTarget.addClass('loading').append(SPINNER);
                    new SuiteInvite.model({
                        user_invited: userId,
                        suite: self.suite.id
                    }).save().done(function() {
                        $currentTarget
                            .removeClass('loading')
                            .addClass('selected')
                            .append(SELECTED)
                            .find('.fa-spinner').remove();
                    });
                }
            });
        },

        renderFoundPeople: function(context, term) {
            var self = this,
                $userSuggest = $('<div/>', {'class': 'user-suggest userSuggest'}),
                ctxt = [];

            this.$('.userSuggest').remove();
            $userSuggest.appendTo(self.$('.userResults'));
            if(context.length || term === '') {
                ctxt = context;
                this.userTeaserTmplPromise.done(function(tmpl) {
                    var $domFragment = $(document.createDocumentFragment()),
                        i, l, item,
                        membersIds,
                        $teaser;
                    membersIds = self.getInvitedIds();
                    for(i=0, l=ctxt.length; i<l; ++i) {
                        item = ctxt[i];
                        $teaser = $(tmpl(item));
                        if(membersIds.indexOf(item.id) > -1) {
                            $teaser.addClass('selected').append(SELECTED);
                        }
                        $domFragment.append($teaser);
                    }
                    if(!term || term === '') {
                    }
                    $userSuggest.append($domFragment);
                });
            } else {
                $userSuggest.append('<div class="nothing">Sorry, we can\'t find "' +  term + '"</div>');
            }
        },

        addMember: function(model) {
            var self = this,
                userUri = model && model.get('resourceUri'),
                invitePromise,
                $dfd = $.Deferred();
            if(!this.chatModel.id && this.chatModel.newonclient) {
                this.chatModel.save().done(function() {
                    self.listenTo(self.chatModel, 'change:members', function() {
                        if(self.foundPeople && self.foundPeople.length) {
                            self.renderFoundPeople(self.foundPeople.toJSON());
                        }
                    });
                    self.addMember(model).done(function() {
                        $dfd.resolve.apply($dfd, arguments);
                    });
                });
                return $dfd.promise();
            }
            invitePromise = this.chatModel.addMember(userUri);
            if(invitePromise) {
                invitePromise.done(function(response) {
                    self.trigger('addedMember', response);
                });
            }
            return invitePromise;
        },

        hide: function() {
            this.$el.hide();
        },

        cancelAddMember: function(e) {
            if(e) {e.preventDefault();}
            this.trigger('cancelAddMember');
        },

        show: function() {
            this.$el.show();
        },

        destroy: function() {
            this.$el.off('.searchuser');
            $(document).off('.searchpeoplepane');
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });

    return InviteToSuiteView;
});