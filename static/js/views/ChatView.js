define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio', 
    'models/Chat',
    'lib/underwood',
    'views/ChatInviteView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    Chat,
    Underwood,
    ChatInviteView
) {
    'use strict';

    var ChatView = Backbone.View.extend({
        events: function() {
            return _.extend({
                'keypress .chatMessageBox': 'msgBoxKeyup',
                'keypress .titleEdit': 'titleKeyup',
                'click .titleEdit': 'startChatTitleEdit',
                'click .newMessage': function(e) {
                    self.$('.newMessage').removeClass('active');
                }
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            var self = this;
            this.model = options.model || null;

            this.chatDetailTmplPromise = suiteio.templateLoader.getTemplate('chat-detail', ['chat-message', 'chat-member-head', 'chat-members']);
            this.chatMsgTemplate = suiteio.templateLoader.getTemplate('chat-message');
            this.topMembersTmplPromise = suiteio.templateLoader.getTemplate('chat-members');
            this.chatMemberTemplate = suiteio.templateLoader.getTemplate('chat-member-head');
            this.emailInviteModalPromise = suiteio.templateLoader.getTemplate('chat-invite-email-modal');

            var $el = $('.pageContainer#chat-'+this.model.id);

            if($el.length) {
                this.setElement($el);
                this.afterRender();
            } else {}

            this.submittedMessage = false;
                        
            this.listenTo(this.model, 'add:members', function(response) {
                // self.enableMessaging();
                if(response && response.user) {
                    this.trigger('addedMember', this.model.id, response);
                    this.renderMembers();
                }
            });
            
            this.listenTo(this.model, 'add:messages', function(msgsToAdd, backwardPageLoad, polled) {
                if(backwardPageLoad) {
                    this._renderOldMessages(msgsToAdd, true);
                } else {
                    if(polled) {
                        console.log('got these from the poller');
                    }
                    this.renderItems(msgsToAdd, polled);
                }
            });

            this.listenTo(this.model, 'delete', function() {
                console.log('deleted a chat');
                suiteio.vent.trigger('deletedChat');
                self.destroy();
            });            
        },

        fetchContext: function() {
            var self = this;
            var url = this.model.get('absoluteUrl');
            return $.ajax({
                url: url,
                type: 'GET',
                data: {
                    spa: true
                }
            });
        },

        render: function() {
            console.log('render!');
            console.log(this.model);
            var self = this;
            var $el;
            var $html;
            var context;
            this.fetchContext().then(function(extraContext) {
                context = $.extend(extraContext, self.model);
                self.model.setChatAttributes(extraContext);
                self.chatDetailTmplPromise.done(function(tmpl) {
                    $html = $(tmpl(context));
                    if($html.length > 1) {
                        $el = $('<div/>').append($html);
                    } else {
                        $el = $html.eq(0);
                    }
                    if(self.$el.is(':empty')) {
                        //first time render
                        self.setElement($el);
                    } else {
                        self.$el.html($html.html());
                    }
                    self.trigger('renderComplete', self.$el);
                }); 
            });
        },

        afterRender: function() {
            console.log('afterRender');
            var self = this;
            if(this.model.get('members').length) {
                this.enableMessaging();
            }
            this.msgEditor = new Underwood(this.$('.chatMessageBox'), {
                placeholder: {
                    hideOnClick: false,
                    text: 'Type your message...'
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
            this.$('.tip').tooltip();
        },

        inviteToChat: function() {
            var self = this;
            var suite = this.model.toJSON();
            this.clearSupplementalViews(['chatInviteView'])
            this.chatInviteView = new ChatInviteView( {
                model: self.model
            });   
            
            this.listenToOnce(this.chatInviteView, 'reRenderChat', function() {
                this.render();
            });            

            this.chatInviteView.openChatInviteModal('settings');
        },
        
        createChat: function(e) {
            this.trigger('startNewChat');
        },

        renderItems: function(items, polled) {
            items = items;
            // // get timestamp from the most recent msg (the last one in our reversed chat layout)
            // this.model.set('currentTimeStamp', items[items.length-1]['created']);
            if(this.model.get(':visible')) {}

            this.$('.orbitalloader').remove();
            var self = this,
                polled = polled || false,
                $domFrag = $(document.createDocumentFragment());
            this.chatMsgTemplate.done(function(tmpl) {
                _(items).each(function(item) {
                    $domFrag.append(tmpl(item));
                });
                self.$('.messageList').append($domFrag);
                if(!polled) {
                    self.scrollToMessage(items[0]['id']);
                } else {
                    self.$('.newMessage').addClass('active');
                }

            });
        },

        selectNewMember: function(e) {
            var self = this;
            var $currentTarget = $(e.currentTarget);
            var $newMember = $currentTarget.data('pk') || '';
            var $selectedResource = $currentTarget.data('uri') || '';
            var email = $currentTarget.data('email') || ''; 

            self.model.addMember($selectedResource);
            self.renderTopMembers();
            
        },

        toggleOtherChatMembers: function(e) {
            this.$('.otherMembers').toggleClass('active');
            this.$('.chatAlsoToggle').toggleClass('active');
        },

        renderTopMembers: function() {
            var self = this,
                $memsContainer = this.$('.membersWrapper'),
                url = '/c/api/chat_top_members/' + this.model.id;
            $.ajax({
                url: url,
                type: 'POST',
                data: {},
                success: function(result) {  
                    self.topMembersTmplPromise.done(function(tmpl) {
                        var memsData = tmpl(result);
                        $memsContainer.html($(memsData));
                        self.$('.tip').tooltip();
                });        
                }
            });
        },

        loadMoreMessages: function() {
            var self = this;
            console.log('loadMoreMessages: starting...');
            this.model.getOlderMessages().done(function(response) {
                if(response && response.objects && response.objects.length) {
                    console.log('got some messages');
                    console.log(response);
                    self._renderOldMessages(response.objects);
                }
            });
        },

        loadNewMessages: function() {
            this.model.getLatestMessages();        
        },

        highlightMessage: function(id) {
            var $msg = this.$('.chatMessage[data-id=' + id + ']');
            $msg.addClass('highlight');
            $msg.switchClass('highlight', '', 3000);
        },
        
        titleKeyup: function(e) {
            var self = this;
            var code = e.charCode || e.keyCode || e.which;
            
            if(code === 27) {
                this.cancelTitleUpdate();
            } else if(code === 13) {
                e.stopPropagation();
                e.preventDefault();
                this.updateTitle()
            }
        },

        cancelTitleUpdate: function() {
            var self = this;
            var $titleEl = this.$('.titleEdit');
            var title = this.model.get('title') || '';
            $titleEl.html(title);
            self.stopChatTitleEdit();
        },

        startChatTitleEdit: function() {
            if(this.editingTitle) {
                return;
            }
            var self = this;
            var $titleEl = this.$('.titleEdit');
                this.chatTitleEditor && this.chatTitleEditor.destroy();
                this.chatTitleEditor =  new Underwood($titleEl, {
                    placeholder: {
                        hideOnClick: false,
                        text: 'Add a subject for this discussion'
                    },  
                    toolbar: false,
                    disableReturn: true
                });
                $titleEl.removeClass('none').focus();
                this.$('.titleUpdateControls').velocity('stop', true).velocity("transition.slideDownIn", 200);
        },

        stopChatTitleEdit: function() {
            var $titleEl = this.$('.titleEdit');
            this.chatTitleEditor && this.chatTitleEditor.destroy();
            $titleEl.blur();
            if(!$titleEl.text()) {
                $titleEl.addClass('none');
            }                            
            this.$('.titleUpdateControls').velocity('stop', true).velocity("transition.slideUpOut", 120);
            this.editingTitle = false;
        },

        updateTitle: function(e) {
            var self = this;
            var $titleEl = this.$('.titleEdit');
            var newTitle = $titleEl.text();

            this.model.set('title', newTitle).save().then(function() {
                console.log('save was successful!');
                self.stopChatTitleEdit();
            });
        },

        // editMessage: function(e) {
        //     var id = $(e.currentTarget).data('id'),
        //         messageModelJSON = this.model.getMessage(id);

        //     if(this.editMessageView && messageModelJSON) {
        //         if(this.editMessageView.currentMsgId === messageModelJSON.id) {
        //             return;
        //         }
        //         this.stopListening(this.editMessageView);
        //         this.editMessageView.destroy();
        //     }
        //     this.editMessageView = new ChatMessageEditView({
        //         messageModelJSON: messageModelJSON,
        //         $el: this.$('.chatMessage[data-id=' + id + ']')
        //     });
        //     this.listenTo(this.editMessageView, 'doneEdit', function() {
        //         this.editMessageView.destroy();
        //         this.stopListening(this.editMessageView);
        //         this.editMessageView = null;
        //     });
        // },

        loadMoreMembers: function() {
            var modelJson = this.model.toJSON(),
                ctxt = {},
                self = this,
                $membersWrapper = this.$('.membersWrapper');
            ctxt = _.extend(ctxt,this._getMembersRenderContext(modelJson.members.slice(5)));

            this.chatMemberTemplate.done(function(tmpl) {
                var $domFrag = $(document.createDocumentFragment());
                for(var i = 0, l = ctxt.length ; i < l ; i += 1) {
                    $domFrag.append(tmpl(ctxt[i]));
                }
                $membersWrapper.addClass('expanded');
                self.$('.moreMembers').before($domFrag);
            });
        },

        _getRenderContext: function() {
            var ctxt = {
                    viewerIsMember: false,
                    viewerIsOwner: false
                },
                modelJson = this.model.toJSON(),
                messages = modelJson.messages,
                cuser = suiteio.loggedInUser;
            console.log(modelJson);
            if(cuser) {
                ctxt.currentUser = cuser.toJSON();
                // if(cuser.id === modelJson.owner.id) {
                //     ctxt.viewerIsOwner = true;
                // }
                if(messages) {
                    console.log('time stamp at the start: ' + this.model.get('currentTimeStamp'));

                    for(var i=0, l=messages.length, message ; i<l ; ++i) {
                        message = messages[i];
                        // console.log(i + ': ' + message.created);
                        if(message.user.id === cuser.id) {
                            message.msgOwnerViewing = true;
                        }
                    }
                }
                if(modelJson.members) {
                    modelJson.members.sort(function(a,b) {
                        if(modelJson.owner.id === a.user.id) {
                            return -1;
                        } else if(cuser && cuser.id === a.user.id && modelJson.owner.id !== b.user.id) {
                            return -1;
                        }
                        return 1;
                    });
                    // if(modelJson.members.length > 5) {
                    //     ctxt = _.extend(ctxt,this._getMembersRenderContext(modelJson.members.slice(0,5)));
                    //     ctxt.moreMembers = modelJson.members.length - 5;
                    // } else {
                    ctxt = _.extend(ctxt,this._getMembersRenderContext(modelJson.members));
                    ctxt.moreMembers = 0;
                    // }
                }
            }
            ctxt = _.extend(ctxt, modelJson);
            return ctxt;
        },

        _getMembersRenderContext: function(members) {
            var modelJson = this.model.toJSON(), ctxt = {},
                cuser = suiteio.loggedInUser;
            for (var o=0, member, lmem=members.length ; o<lmem ; ++o) {
                member = members[o];
                if(modelJson.owner.id === cuser.id) {
                    member.memOwnerViewing = true; //member context, allow owner to remove any members
                }
                if(member.user.id === cuser.id) {
                    member.memOwnerViewing = true; //member context, allow viewer to remove herself from chat
                    ctxt.viewerIsMember = true; //global context, indicates viewer is a member of the chat
                    ctxt.onlyMember = (members.length === 1);
                }
                if(modelJson.owner.id === member.user.id) {
                    member.isOwner = true; //member context, identify owner's head
                }
            }
            return ctxt;
        },
      
        deleteChat: function(e) {
            var self = this;
            if(!suiteio.loggedInUser) {
                suiteio.fireLoginModal();
                } else { 
            if(!this.model.get('ownerViewing')) {
                return; }
                e.preventDefault();
                var self = this;
                suiteio.notify.prompt({
                    msg: 'Are you sure you want to delete this discussion?'
                }).done(function(decision) {
                    if(decision) {
                        self.model.deleteChat(self.model.id, suiteio.loggedInUser);
                    }
                });
            }
        },

        deleteMessage: function(e) {
            var $ctarget = $(e.currentTarget),
                $msg = $ctarget.closest('.chatMessage'),
                id = $ctarget.data('id'),
                self = this,
                deleteMsg;
            suiteio.notify.prompt({
                msg: 'Delete this message?'
            }).done(function(decision) {
                if(decision) {
                    deleteMsg = self.model.deleteMessage(id);
                    if(deleteMsg && deleteMsg.done) {
                        deleteMsg.done(function() {
                            $msg.remove();
                        });
                    }
                }
            });
        },

        deleteMemberAction: function(e) {
            if(e) { e.preventDefault(); }
            var $ctarget = $(e.currentTarget),
                id = $ctarget.data('chatId'),
                uid = $ctarget.data('userId');
            this.deleteMember(id, uid);
        },

        deleteMember: function(id, userId, skipPrompt) {
            var self = this;
            if(userId === this.model.get('owner').id) {
                suiteio.notify.alert({
                    msg: 'You can\'t remove this discussion\'s creator.'
                });
                return;
            }
            if(skipPrompt) {
                this._doDeleteMember(id, userId);
            } else {
                suiteio.notify.prompt({
                    msg: 'Remove this person?'
                }).done(function(decision) {
                    if(decision) {
                        self._doDeleteMember(id, userId);
                    }
                });
            }
        },

        _doDeleteMember: function(id, userId) {
            var self = this,
                removeMember = self.model.removeMember(id, userId);
            if(removeMember && removeMember.done) {
                removeMember.done(function() {
                    self.$('.memberHead[data-id='+ id + ']').remove();
                });
            }
        },

        endEdit: function() {
            this.msgEditor.destroy();
        },

        enableMessaging: function() {
            this.$('.chatMessageBox').prop('disabled', false);
            this.$('.sendMessageBtn').prop('disabled', false);
        },

        msgBoxKeyup: function(e) {
            var code = e.charCode || e.keyCode || e.which;
            if(code === 13 && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                this.sendMessage();
            }
        },

        jumpToMessage: function(e) {
            e.preventDefault();
            var msgId = $(e.currentTarget).data('msgId');
            var $chatMsg = this.$('.chatMessage[data-id=' + msgId + ']');
            $('body').animate({scrollTop: $chatMsg.position().top-100}, 'fast');
        },

        sendMessage: function(e) {
            var self = this,
                newUrl,
                $send,
                loggedInUser = suiteio.loggedInUser,
                addMemberPromise;
            if(e) {
                e.preventDefault();
            }
            $send = this.$('.sendMessageBtn').dynamicButton({immediateEnable: true});

            var message = this.$('.chatMessageBox').html();
            var alertIsOpen = $('.alertsContainer .alert').html(); // detect if an alert is open
            if(alertIsOpen){
                this.submittedMessage = true;
                $send.dynamicButton('revert');
                return;
            } else {
                this.submittedMessage = false;
            }

            if(!message || message.match(/^\s+$/)) {
                suiteio.notify.alert({
                        msg:'Oops! Please type your message before trying to submit it.',
                        delay: 5000
                    });
                 $send.dynamicButton('revert');
                 this.$('.chatMessage').removeClass('obscureButt');
                return;
            }
            
            this.model.sendMessage(message).done(function(response) {
                $send.dynamicButton('revert');
                self.$('.chatMessageBox').html('');
                //make sure we don't append twice. sometimes polling would already have appended the new message
                self._renderMessage(response);
                self.renderTopMembers();
                if(self.justCreated) {
                    console.log('the chat was just created and the message is now submitted; safe to reload now');
                    self.trigger('createdChat', self.model.id);
                }
            });
            // this.scrollToMessageBox();

        },

        scrollToMessage: function(msgId) {
                var $element = this.$('.chatMessage[data-id=' + msgId + ']');
                 this.$('.chatMessage[data-id=' + msgId + ']').velocity("scroll", { 
                container: this.$('.modalScrollable'),
                  duration: 200,
                  offset: -200
                });

            // this.scrollEl.animate({scrollTop: this.scrollEl.position().top}, 200);

        },

        flagMessage: function(e) {
            suiteio.flagIt(e);
        },

        _renderOldMessages: function(msgs, backwardPageLoad) {
            var self = this,
                $domFragment = $(document.createDocumentFragment()),
                ctxt = {};
            this.chatMsgTemplate.done(function(tmpl) {
                for(var i=msgs.length-1, msg ; i>=0 ; --i) {
                    msg = msgs[i];
                    if(suiteio.loggedInUser && msg.user.id === suiteio.loggedInUser.id) {
                        ctxt.msgOwnerViewing = true;
                    }
                    $domFragment.prepend(tmpl(_.extend(ctxt, msg)));
                }
                if(backwardPageLoad) {
                    self.$('.messageList .loadMore').after($domFragment);
                    if(self.model.messagesCollection.bottomed) {
                        self.$('.messageList .loadMore').remove();
                    }
                } else {
                    self.$('.messageList').prepend($domFragment);
                }
            });
        },

        _renderMessage: function(response) {
            var self = this;
            if(self.$('.chatMessage[data-id=' + response.id + ']').length) {
                //if message is already rendered
                return;
            }
            this.chatMsgTemplate.done(function(tmpl) {
                response.msgOwnerViewing = true;
                self.$('.messageList').append(tmpl(response));
                self.scrollToMessage(response.id);
                self.$('.chatMessageBox').empty().focus();
            });
        },

        clearSupplementalViews: function() {
            var views = ['chatInviteView'];
            for(var view, i = 0, l = views.length ; i < l ; i += 1) {
                view = views[i];
                if(this[view]) {
                    this[view].destroy();
                    this.stopListening(this[view]);
                    this[view] = null;
                }
            }
        },

        destroy: function() {
            this.msgEditor && this.msgEditor.destroy();
            this.metaEditor && this.metaEditor.destroy();
            
            // this.$el.remove();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return ChatView;
});