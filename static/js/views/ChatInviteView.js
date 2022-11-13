// ChatInviteView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/PagedListView',
    'models/ChatMember',
    'lib/underwood'
], function(
    $,
    Backbone,
    _,
    suiteio,
    PagedListView,
    ChatMember,
    Underwood
    ) { 
    'use strict';
    var ChatInviteView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'click .showUserSettings': 'slideOpenUserTab',
                'click .showSettings': 'userTabGoodbye',
                'click .userSelect': 'addMember'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            var self = this;
            this.options = options;
            this.suite = this.options.suite;
            this.model = options.model;
            this.membersArray = this.model.get('members'); // existing members, which we can glean from the model

            this.chatInviteModalTmplPromise = suiteio.templateLoader.getTemplate('chat-invite-modal');
            this.userInviteItemTmplPromise = suiteio.templateLoader.getTemplate('user-invite-item');
        },

        openChatInviteModal: function() {  
            var self = this;

            self.chatInviteModalTmplPromise.done(function(tmpl) {
                self.chatInviteModal = $(tmpl({
                    storyTitle: self.contentTitle
                }));
                self.chatInviteModal.modal(); 
                self.setElement(self.chatInviteModal);
                self.setupPagedList();        
                self.loadMemberLists();
            });

        },

        setupPagedList: function() {
            var self = this;
            var $listViewEl = this.$('.chatMemberSearch');
            var startPage = 1;
            var searchArr = window.location.search.split('=');
            var namedFilter = this.namedFilter || '';
            var loadFirstPage = true;
            if(searchArr.length >= 2 && searchArr[0] === '?page') {
                startPage = +searchArr[1];
            }
            var url = '/u/api/neighbours';

            this.chatInviteList && this.chatInviteList.destroy();
            this.chatInviteList = new PagedListView({
                firstPage: loadFirstPage,
                namedFilter: namedFilter,
                el: $listViewEl,
                url: url,
                templateName: 'user-invite-item',
                name: 'chatInviteList'
            });
            this.listenTo(self.chatInviteList, 'listViewFiltered', function(namedFilter) {
                namedFilter = namedFilter || '';
                // if(namedFilter=='suite') {
                //     this.chatInviteList.templateName = 'suite-story-teaser';
                // } else if(namedFilter=='user') {
                //     this.chatInviteList.templateName = 'user-teaser';
                // }
                self.chatInviteList.fetch();
            });            
            this.listenToOnce(self.chatInviteList, 'listViewReady', function() {
                self.chatInviteList.fetch();
            });            
        },

        addMember: function(e) {
            var self = this;
            var $currentTarget = $(e.currentTarget);
            // var userEmail = $currentTarget.data('email');
            var userId = $currentTarget.data('pk');
            this.model.addMember(userId).done(function(user) {
                self.loadMembers();
            });            
            // this.membersArray.unshift(newMember);
            // this.resetSearchList();
        },

        loadMemberLists: function() {
            // todo: get email invites
            this.loadMembers();
            this.loadInvites();
        },

        loadMembers: function() {
            console.log('loading members');
            this.membersArray
            this.chatMemberCollection = new ChatMember.collection({}, {chatId: this.model.id});
            console.log(this.chatMemberCollection);

            this.refreshMemberList();
        },

        refreshMemberList: function() {
            this.listenToOnce(this.chatMemberCollection, 'reset', this.renderMemberList);
            this.chatMemberCollection.fetch({reset: true});
        },

        loadInvites: function() {
            console.log('load invites');
            // pending, non-member emails (custom fetch)
        },

        renderInitialMembers: function() {
            var self = this;
            var ctxt = this.membersArray;
            if(ctxt && ctxt.length) {
                this.userInviteItemTmplPromise.done(function(tmpl) {
                    var $domFrag = $(document.createDocumentFragment());
                    for(var i=0, l=ctxt.length, element ; i<l ; ++i) {
                        element = ctxt[i];
                        element['selected'] = true;
                        if(element['id']==suiteio.loggedInUser.id) {
                            element['isYou'] = true;
                        }
                        $domFrag.append(tmpl(element));
                    }
                    self.$('.inviteList').html($domFrag);
                });
            }
        },
        refreshInviteList: function() {
            // this.listenToOnce(this.suiteInviteCollection, 'reset', this.renderInviteList);
            // this.suiteInviteCollection.fetch({reset: true});
        },

        deleteInvite: function(e) {
            // var $currentTarget = $(e.currentTarget);
            // var id = $currentTarget.data('id');
            // var self = this;
            // self.suiteInviteCollection.removeThisInvite(id);
            // $currentTarget.closest('.pendingMember').remove();
        },

        // changeMemberStatus: function(e) {
        //     var self = this;
        //     var $currentTarget = $(e.currentTarget);
        //     var id = $currentTarget.data('id');
        //     var status = $currentTarget.data('status');
        //     // once?
        //     this.listenToOnce(this.suiteMemberCollection, 'change:status', function() {
        //         self.renderMemberList();
        //     });
        //     this.suiteMemberCollection.get(id).changeMemberStatus(status);
        // },

        renderInviteList: function() {
            var self = this,
                ctxt = this.suiteInviteCollection.toJSON();
                self.chatMemberCollection.done(function(tmpl) {
                    var $inviteFrag = $(document.createDocumentFragment());
                    for(var i=0, l=ctxt.length, member ; i<l ; ++i) {
                        member = ctxt[i];
                        $inviteFrag.append(tmpl(member));
                    }
                    $('.inviteList').html($inviteFrag);
                });
        },

        renderMemberList: function() {
            console.log('rendering....');
            var self = this,
                ctxt = this.chatMemberCollection.toJSON();
                console.log(ctxt);
                self.userInviteItemTmplPromise.done(function(tmpl) {
                    var $domFrag = $(document.createDocumentFragment());
                    for(var i=0, l=ctxt.length, member ; i<l ; ++i) {
                        member = ctxt[i]['user'];
                        $domFrag.prepend(tmpl(member));
                    }
                    $('.memberList').html($domFrag);
                });
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
                 msg: 'Are you sure you want to remove ' + userName + ' from this discussion?'
             }).done(function(decision) {
                if(decision) {
                    self.listenToOnce(self.chatMemberCollection, 'destroy', function() {
                        self.renderMemberList();
                    });
                    self.chatMemberCollection.removeThisUser(userId);
                    // self.$('.userTeaser[data-id=' + id + ']').remove();
                }
            });
         },

        hide: function() {
            this.$el.hide();
        },

        show: function() {
            this.$el.show();
        },

        destroy: function() {
            this.chatInviteList && this.chatInviteList.destroy();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return ChatInviteView;

});