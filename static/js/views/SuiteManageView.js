// SuiteManageView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'lib/underwood',
    'models/SuiteMember',
    'models/SuiteInvite',
    'models/SuiteRequest',    
    // 'lib/Countable',
    'lib/bindWithDelay', // no exports
    'helpers/jquery.autoExpandTextarea' //no exports
], function(
    $,
    Backbone,
    _,
    suiteio,
    Underwood,
    SuiteMember,
    SuiteInvite,
    SuiteRequest    
    // Countable
    ) { 
    'use strict';
    var SuiteManageView = Backbone.View.extend({
        el: '[data-view-bind=SuiteManageView]',
        events: function() {
            return _.extend({
                'click .showUserSettings': 'slideOpenUserTab',
                'click .showSettings': 'userTabGoodbye'

            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            var self = this;
            this.options = options;
            this.suite = this.options.suite;
            this.model = options.model;
            this.members = this.suite.suiteMembers;
            this.memsRequested = this.suite.requestedMembers || '';
            this.memsInvited = this.suite.invitedMembers || '';

            this.viewname= 'suitemanageview';
            this.suiteManageModalTmplPromise = suiteio.templateLoader.getTemplate('suite-manage-modal');
            this.suiteMemberTmplPromise = suiteio.templateLoader.getTemplate('suite-member-item');
            this.userInviteItemTmplPromise = suiteio.templateLoader.getTemplate('user-invite-item');
        },

        doQuickSearch: function(query) {
            var self = this, 
                objectId = this.model.id,
                objectType = 'suite',
                $quicksearchResults = $('.inviteSearchResults'),
                quickSearchInput = $('.quickSearchInput'),
                query = quickSearchInput.val();

            if(!query){
                self.resetQuickSearch();
                return;
            }
            self.$('.inviteSearchResults').addClass('active');
            $quicksearchResults.append(this.loader);

            $.ajax({
                url: '/u/api/neighbours',
                type: 'POST',
                data: {
                    q: query,
                    objectid: objectId,
                    objtype: objectType,
                    invite: true
                },
                success: function(data) {

                    if(data.objects) {
                        self.renderQuickSearchResults(data);
                        self.$('.withResults').addClass('active');
                        $quicksearchResults.addClass('active');
                        self.$('.quickSearchInput').blur();
                    } else {
                        self.clearQuickSearchResults();
                    }
                },
                error: function() {
                    // self.resetQuickSearch();
                }
            });
        },

        quickSearchInputKeyup: function(e) {
            var code = e.charCode || e.keyCode || e.which;
            if(code === 13) {
                e.preventDefault();
            } 
            if(code === 27) {
                this.resetQuickSearch();   
                return;
            }
            this.doQuickSearch(e);

        },

        clearQuickSearchResults: function() {
            $('.inviteSearchResults').html("").removeClass('active');
        },

        resetQuickSearch: function() {
            $('.quickSearchInput').val('');
            $('.inviteSearchResults').html("").removeClass('active');
            $('.quickSearchInput').focus();
        },

        renderQuickSearchResults: function(data, email) {
            var self = this;
            var $inviteSearchResults = $('.inviteSearchResults'),
                ctxt = data.objects;
            var email = email || '';

            if(ctxt && ctxt.length) {
                self.userInviteItemTmplPromise.done(function(tmpl) {
                    var $domFrag = $(document.createDocumentFragment());
                    for(var i=0, l=ctxt.length, element ; i<l ; ++i) {
                        element = ctxt[i];
                        element.invited = true;
                        $domFrag.append(tmpl(element));
                    }
                    $('.inviteSearchResults').html($domFrag);
                });
            }

        },

        slideOpenUserTab: function() {
            var self = this;
            // this.$('.suiteSettingsTab').removeClass('active');
            this.$('.suiteUserSettingsTab').addClass('active');            
            this.$('.slideFromRight').velocity('stop', true).velocity({ left: 0 }, {
              duration: 260,
              easing: [ 0.19, 1, 0.22, 1 ]
            });  

            var wait = setTimeout(function() { 
                self.setupUserTab();
             }, 240);
        },

        userTabGoodbye: function() {
            var self = this;
            var cardWidth = this.cardWidth || 540;
            this.$('.slideFromRight').velocity('stop', true).velocity({ left: cardWidth }, {
              duration: 260,
              easing: [ 0.19, 1, 0.22, 1 ]
            });
            var wait = setTimeout(function() { 
                self.$('.suiteSettingsTab').addClass('active');
                self.setupSettingsTab();
             }, 80);
            var wait = setTimeout(function() { 
                self.$('.suiteUserSettingsTab').removeClass('active');
             }, 260);
        },

        setupUserTab: function() {
            var self = this;                  
            this.loadMemberLists();
            var $membersArray = [];
            $('.quickSearchInput').focus();    
        },

        setupSettingsTab: function() {
            // this.loadMemberLists();                   
            $('.newSuiteTitle').focus();
            this.manageTitleEditor = new Underwood($('.manageSuiteTitle'), {
                toolbar: false,
                disableReturn: true
            });
            this.manageDescEditor = new Underwood($('.manageSuiteDesc'), {
                toolbar: false,
                disableReturn: true
            });
        },

      openSuiteManageModal: function(tab) {
            var self = this;
            var userTab = !!(tab == 'users');

            self.suiteManageModalTmplPromise.done(function(tmpl) {
                var $manageModal = $(tmpl({
                        suite: self.suite,
                        csrf: suiteio.csrf,
                        userTab: userTab
                }));
                $manageModal.modal({expandIn: true, duration: 300 }); 
             
                if(userTab) {
                    self.setupUserTab();
                } else {
                    self.setupSettingsTab();
                }

                self.setElement($('.suiteManageModal'));
                self.cardWidth = self.$('.modalCard').width();

                $manageModal.bindWithDelay('keypress', '.quickSearchInput', function(e) {
                    self.quickSearchInputKeyup(e);
                }, 1000, true);

                $manageModal.on('click', '.saveSuiteSettings', function(e) {
                    self.saveSuiteSettings(e);
                });

                // $('.manageTitle').append(' <span class="wordcount titleCount"></span>');
                // this.countable = Countable.live($('.newSuiteTitle').get(0), function(counter) {
                //     self.updateWordCount(80, counter.characters, 'title');
                // });

                // $('.manageDesc').append('<span class="wordcount descCount"></span>');
                // this.countable = Countable.live($('.newSuiteDesc').get(0), function(counter) {
                //     self.updateWordCount(140, counter.characters, 'description');
                // });

                $manageModal.on('click', '.fancySwitch', function(e) {
                    var $privacySwitch = $('.newSuitePrivacy');
                    $privacySwitch.toggleClass('on').toggleClass('off');
                    if($privacySwitch.hasClass('on')) {
                        $privacySetting = true;
                    } 
                });

                $manageModal.on('click', '.revokeInvite', function(e) {
                    self.deleteInvite(e);
                });

                $manageModal.on('click', '.promoteMember', function(e) {
                    self.changeMemberStatus(e);
                });

                $manageModal.on('click', '.removeMember', function(e) {
                    self.removeMember(e);
                });

                $manageModal.on('click', '.demoteMember', function(e) {
                    self.changeMemberStatus(e);
                });

                $manageModal.on('click', '.toggleSuitePrivacy', function(e) {
                    self.toggleSuitePrivacy(e);
                });


                $manageModal.on('click', '.toggleActiveHeroSetting', function(e) {
                    self.toggleActiveHeroSetting(e);
                });

                
                $manageModal.on('click', '.inviteSearchResults .pendingMember', function(e) {
                    // create the suite invite, add to list

                    var $currentTarget = $(e.currentTarget);
                    var $newMember = $currentTarget.data('pk') || '';
                    var email = $currentTarget.data('email') || '';
                    
                    self.addNewInvite($newMember, email);
                    self.resetQuickSearch();
                });

                // $manageModal.on('click', '.removeMember', function(e) {
                //     var $currentTarget = $(e.currentTarget),
                //         item = $currentTarget.closest('.pendingMember'),
                //         itemPk = item.data('pk');
                //     item.remove();
                //     var i = $membersArray.indexOf(itemPk);
                //     if(i != -1) {
                //         $membersArray.splice(i, 1);
                //     }
                //     self.updateExclusionList(itemPk,true);
                // });

            });
        },

        addNewInvite: function(invitedPk, invitedEmail) {
            var self = this;
            var invitedPk = invitedPk || '';
            var invitedEmail = invitedEmail || '';

            // create a client-side model
            var suiteInvite = new SuiteInvite.model({
                user_inviting: suiteio.loggedInUser,
                user_invited: invitedPk,
                email: invitedEmail,
                suite: this.suite.id
            }).save().done(function(){
                // self.suiteInviteCollection.add(suiteInvite).save();
                // now refresh the invite list
                self.loadInvites();
            });
            
        },

        loadMemberLists: function() {
            // todo: get email invites
            this.loadMembers();
            this.loadInvites();
            this.loadRequests();
        },

        updateSuiteRequestStatus: function(e) {
            var $target = $(e.currentTarget),
                requestId = $target.data('id'),
                status = $target.data('status'),    
                url = '/s/api/request_action/' + requestId;

            $.ajax({
                url: url,
                type: 'POST',
                data: {
                    stat: status = status
                },
                success: function() {
                    var thanksMsg = '<p class="thanks-response">Done! You can view your old notifications by clicking the <strong>READ</strong> tab above</p>',
                        parent = $target.closest('.pendingMember');
                    parent.remove();
                }
            });
        },

        saveSuiteSettings: function(e) {
            var self = this;
            var $target = $(e.currentTarget);

            var newName = $('.manageSuiteTitle').html();
            var newDesc = $('.manageSuiteDesc').html();
            var newPrivacy = false;
            var newActiveHero = true;

            var suiteData = {
                name: newName,
                description: newDesc,
                privacy: newPrivacy,
                activeHero: newActiveHero
            }
            self.model.set(suiteData).save().done(function() {
                self.trigger('reRenderSuite');  
            });
        },

        loadMembers: function() {
            // if(!this.suiteMemberCollection) {
                this.suiteMemberCollection = new SuiteMember.collection({}, {suiteId: this.model.id});
                this.refreshMemberList();
            // }
        },

        refreshMemberList: function() {
            this.listenToOnce(this.suiteMemberCollection, 'reset', this.renderMemberList);
            this.suiteMemberCollection.fetch({reset: true});
        },

        loadInvites: function() {
            // if(!this.suiteInviteCollection) {
                this.suiteInviteCollection = new SuiteInvite.collection({}, {suiteId: this.model.id});
                this.refreshInviteList();
            // }
        },

        refreshInviteList: function() {
            this.listenToOnce(this.suiteInviteCollection, 'reset', this.renderInviteList);
            this.suiteInviteCollection.fetch({reset: true});
        },

        deleteInvite: function(e) {
            var $currentTarget = $(e.currentTarget);
            var id = $currentTarget.data('id');
            var self = this;
            self.suiteInviteCollection.removeThisInvite(id);
            $currentTarget.closest('.pendingMember').remove();
        },

        changeMemberStatus: function(e) {
            var self = this;
            var $currentTarget = $(e.currentTarget);
            var id = $currentTarget.data('id');
            var status = $currentTarget.data('status');
            // once?
            this.listenToOnce(this.suiteMemberCollection, 'change:status', function() {
                self.renderMemberList();
            });
            this.suiteMemberCollection.get(id).changeMemberStatus(status);
        },

        loadRequests: function() {
            if(!this.suiteRequestCollection) {
                this.suiteRequestCollection = new SuiteRequest.collection({}, {suiteId: this.model.id});
                this.listenToOnce(this.suiteRequestCollection, 'reset', this.renderRequestList);
                this.suiteRequestCollection.fetch({reset: true});
            }
        },

        renderInviteList: function() {
            var self = this,
                ctxt = this.suiteInviteCollection.toJSON();
                self.suiteMemberTmplPromise.done(function(tmpl) {
                    var $inviteFrag = $(document.createDocumentFragment());
                    for(var i=0, l=ctxt.length, member ; i<l ; ++i) {
                        member = ctxt[i];
                        $inviteFrag.append(tmpl(member));
                    }
                    $('.inviteList').html($inviteFrag);
                });
        },

        renderRequestList: function() {
            var self = this,
                ctxt = this.suiteRequestCollection.toJSON();

                self.suiteMemberTmplPromise.done(function(tmpl) {
                    var $domFrag = $(document.createDocumentFragment());
                    for(var i=0, l=ctxt.length, member ; i<l ; ++i) {
                        member = ctxt[i];
                        $domFrag.append(tmpl(member));
                    }
                    $('.requestList').html($domFrag);
                });
        },

        renderMemberList: function() {
            var self = this,
                // ctxt = this.suiteMemberCollection.pluck('user');
                ctxt = this.suiteMemberCollection.toJSON();
                self.suiteMemberTmplPromise.done(function(tmpl) {
                    var $domFrag = $(document.createDocumentFragment());
                    for(var i=0, l=ctxt.length, member ; i<l ; ++i) {
                        member = ctxt[i];
                        $domFrag.prepend(tmpl(member));
                    }
                    $('.memberList').html($domFrag);
                });
        },

        toggleSuitePrivacy: function(e) {
            var self = this;
            var $currentTarget = $(e.currentTarget);
            var makePrivate = !!$currentTarget.data('private');
            var priv = (makePrivate ? "public" : "private");

            self.model.set({private: makePrivate}).save().done(function(){
                suiteio.notify.alert({
                    kiss: true,
                    msg: 'Updated',
                    delay: 750
                });         
                $('.toggleSuitePrivacy').toggleClass('checked');
            });
        },

        toggleActiveHeroSetting: function(e) {
            var self = this;
            var $currentTarget = $(e.currentTarget);
            var makeActive = !!$currentTarget.hasClass('checked');

            self.model.set({activeHero: makeActive}).save().done(function(){
                suiteio.notify.alert({
                    kiss: true,
                    msg: 'Updated',
                    delay: 750
                });         
                $('.toggleActiveHeroSetting').toggleClass('checked');
            });
        },

        ignoreRequest: function(e) {
            try { e.preventDefault(); } catch(evt) {}
            var id = $(e.currentTarget).data('id');
            this.listenToOnce(this.suiteRequestCollection, 'change:status', this.updateRequestRender);
            this.suiteRequestCollection.get(id).ignoreRequest();
        },

        acceptRequest: function(e) {
            try { e.preventDefault(); } catch(evt) {}
            var id = $(e.currentTarget).data('id');
            this.listenToOnce(this.suiteRequestCollection, 'change:status', this.updateRequestRender);
            this.suiteRequestCollection.get(id).acceptRequest();
        },

        removeMember: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            e.stopPropagation();
            e.preventDefault();
            var userId = $target.data('id');
            var userName = $target.data('name');
            suiteio.notify.prompt({
                no: 'No',
                yes: 'Yes',
                 msg: 'Are you sure you want to remove ' + userName + ' from this Suite?'
             }).done(function(decision) {
                if(decision) {
                    self.listenToOnce(self.suiteMemberCollection, 'destroy', function() {
                        self.renderMemberList();
                    });
                    self.suiteMemberCollection.removeThisUser(userId);
                    // self.$('.userTeaser[data-id=' + id + ']').remove();
                }
            });
         },

        deleteSuite: function() {
            if(!suiteio.loggedInUser) { return; }
            var self = this, 
                url = '/s/api/delete',
                $slug = suiteio.loggedInUser.get('slug');
            suiteio.notify.prompt({
                msg: 'Are you sure you want to delete this Suite?'
            }).done(function(decision) {
                if(decision) {
                    $.ajax({
                        url: url,
                        type: 'POST',
                        data: {
                            pk: self.model.id
                        },
                        success: function(result) {
                            if(result) {
                                self.model.destroy({
                                    wait: true,
                                    success: function() {
                                        self.modelDeleted = true;
                                        window.location = '/' + $slug;
                                    }
                                });
                            } else {
                                suiteio.notify.alert({
                                 msg: 'Something went wrong deleting this Suite. Engineers have been alerted.'
                                 });
                            }
                        }
                    });
               }     
                            
            });
        },

        updateWordCount: function(limit, chars, field) {
            var remaining = limit - chars;
            var total = chars + '/' + limit; 
            if(field == 'description') {
                var container = $('.descCount');
            } else if(field == 'title') {
                var container = $('.titleCount');
            }
            container.html(total);
            if(chars>limit) {
                container.addClass('over');
            } else if(container.hasClass('over')) {
                container.removeClass('over');
            }
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
                        $teaser;
                    for(i=0, l=ctxt.length; i<l; ++i) {
                        item = ctxt[i];
                        $teaser = $(tmpl(item));
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

        hide: function() {
            this.$el.hide();
        },

        show: function() {
            this.$el.show();
        },

        destroy: function() {
            this.$el.off('.searchuser');
            this.manageTitleEditor && this.manageTitleEditor.destroy();
            this.manageTitleEditor && this.manageDescEditor.destroy();
            $(document).off('.searchpeoplepane');
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });

    return SuiteManageView;

});