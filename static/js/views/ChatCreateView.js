define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/PagedListView',
    'lib/underwood'
], function(
    $,
    Backbone,
    _,
    suiteio,
    PagedListView,
    Underwood
) {
    'use strict';
    var ChatCreateView = Backbone.View.extend({
        events: function() {
            return _.extend({

                'click .doAddRemove': 'doAddRemove',
                'hide.bs.modal': 'exit',
                'keypress .miniCreateInput': 'miniSuiteCreateInputKeyup',
                'click .suiteCreateSearchResults .pendingMember': 'addMemberToList',
                'click .userSelect': 'addMember',
                'focus .chatMessage': 'focusMessage',
                'blur .chatMessage': 'unFocusMessage'

            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            this.options = options;
            this.utilityUrl = '/c/api/chat_create';
            this.membersArray = [suiteio.loggedInUser.toJSON()];
            this.chatWith = options.chatWith || '';

            this.chatCreateModalPromise = suiteio.templateLoader.getTemplate('chat-create-modal');
            this.userInviteItemTmplPromise = suiteio.templateLoader.getTemplate('user-invite-item');
        },

        openChatCreateModal: function() {  
            var self = this;

            self.chatCreateModalPromise.done(function(tmpl) {
                self.chatCreateModal = $(tmpl({
                    storyTitle: self.contentTitle
                }));
                self.chatCreateModal.modal(); 
                self.setElement(self.chatCreateModal);

                if(self.chatWith && self.chatWith != suiteio.loggedInUser.id) {
                    self.fetchUserObject(self.chatWith).then(function(newUser) {
                        console.log(newUser);
                        if(newUser) {
                            self.membersArray.unshift(newUser);        
                            self.renderInitialMembers();
                        }
                    }); 
                } else {
                    self.renderInitialMembers(); 
                }
                self.setupPagedList();        
                self.setupMessageEditor();
            });

        },

        fetchUserObject: function(pk) {
            var self = this;
            return $.ajax({
                url: '/u/api/user/' + pk,
                type: 'POST'
            });
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

        setupMessageEditor: function() {
            this.firstMsgEditor = new Underwood(this.$('.chatMessage'), {
                placeholder: {
                    hideOnClick: false,
                    text: 'Type the first message...'
                },  
                autoLink: true,
                toolbar: {
                    updateOnEmptySelection: true,
                    buttons: [
                        'anchor',
                        'bold',
                        'italic'                  ]
                },
                spellcheck: false,
                imageDragging: false,
                fileDragging: false,
                anchorPreview: true,
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

            this.chatCreateList && this.chatCreateList.destroy();
            this.chatCreateList = new PagedListView({
                firstPage: loadFirstPage,
                namedFilter: namedFilter,
                el: $listViewEl,
                url: url,
                templateName: 'user-invite-item',
                name: 'chatcreatelist'
            });
            this.listenTo(self.chatCreateList, 'listViewFiltered', function(namedFilter) {
                namedFilter = namedFilter || '';
                // if(namedFilter=='suite') {
                //     this.chatCreateList.templateName = 'suite-story-teaser';
                // } else if(namedFilter=='user') {
                //     this.chatCreateList.templateName = 'user-teaser';
                // }
                self.chatCreateList.fetch();
            });            
            this.listenToOnce(self.chatCreateList, 'listViewReady', function() {
                self.chatCreateList.fetch();
            });            
        },

        addMember: function(e) {
            var $currentTarget = $(e.currentTarget);
            // var userEmail = $currentTarget.data('email');
            var userId = $currentTarget.data('pk');
            var newMember = this.chatCreateList.collection.findWhere({id: userId }).toJSON();
            this.membersArray.unshift(newMember);
            this.resetSearchList();
        },

        removeMember: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            // var userEmail = $currentTarget.data('email');
            var userId = $target.data('id');
            this.membersArray = $.grep(self.membersArray, function(e){ return e.id != userId; });
            this.resetSearchList();
        },  

        resetSearchList: function() {
            this.$('.paginatedList').html('');
            this.$('.ctxtSearchInput').val('');
            this.chatCreateList && this.chatCreateList.destroy();
            this.renderInitialMembers();
        },

        focusMessage: function() {
           this.$('.firstMessage').velocity('stop', true).velocity({ height: 520 }, {
              duration: 120
            });
        },
          
        unFocusMessage: function() {
           this.$('.firstMessage').velocity('stop', true).velocity({ height: 34 }, {
              duration: 120
            });
        },

        createIt: function(e) {
            var self = this;
            var $currentTarget = $(e.currentTarget);
            var url = this.utilityUrl;
            var message = this.$('.chatMessage').html() || '';
            console.log('the message is ' + message);
            var membersArray = this.membersArray;
            
            var $createNewChat = $.ajax({
                url: url,
                type: 'POST',
                data: {
                    message: message,
                    members: JSON.stringify(membersArray),
                }
            });
            $createNewChat.then(function(chatUrl) {
                self.trigger('newChatCreated', chatUrl)
            });
        },

        exit: function() {
            this.trigger('closeChatCreate');
        },

         destroy: function() {
            this.firstMsgEditor && this.firstMsgEditor.destroy();
            this.chatCreateList && this.chatCreateList.destroy();
            Backbone.View.prototype.destroy.apply(this, arguments);
            this.$el.remove();
        }

    });
    return ChatCreateView;
});


