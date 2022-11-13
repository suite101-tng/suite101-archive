define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'lib/Countable',
    'views/PagedListView',
    'lib/underwood'
], function(
    $,
    Backbone,
    _,
    suiteio,
    Countable,
    PagedListView,
    Underwood
) {
    'use strict';
    var SuiteCreateView = Backbone.View.extend({
        events: function() {
            return _.extend({

                'click .doAddRemove': 'doAddRemove',
                'hide.bs.modal': 'exit',
                'click .userSelect': 'addMember',
                'click .removeQuickSearchItem': 'removeMemberFromList',
                'click .createSuite': 'createIt'

            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            this.options = options;
            this.viewname= 'suitecreateview';
            this.membersArray = [suiteio.loggedInUser.toJSON()];
            this.privacySetting = false;
            this.addingTo = options.addingTo || false;

            this.suiteCreateEditors = {};
            this.editorEls = ['newSuiteDesc', 'newSuiteTitle'];   

            this.suiteCreateModalPromise = suiteio.templateLoader.getTemplate('suite-create-modal');
            this.userInviteItemTmplPromise = suiteio.templateLoader.getTemplate('user-invite-item');
        },
 
        render: function() {
            var self = this;
            this.openSuiteCreateModal()
        },

       openSuiteCreateModal: function(options) {
            var self = this;

            self.suiteCreateModalPromise.done(function(tmpl) {
                var $createModal = $(tmpl({
                        csrf: suiteio.csrf,
                        private: self.privacySetting
                }));
               
                $createModal.modal(); 
                self.setElement($createModal);

                $(' #card-0').addClass('active');
                $('.miniHeroSubnav .notch-0').addClass('active');
                $('.newSuiteTitle').focus();

                $('.suiteTitleContainer').append('<span class="fixed-right-wordcount titleCount"></span>');
                this.countable = Countable.live(self.$('.newSuiteTitle').get(0), function(counter) {
                    self.updateWordCount(80, counter.characters, 'title');
                });

                $('.suiteDescriptionContainer').append('<span class="fixed-right-wordcount descCount"></span>');
                this.countable = Countable.live(self.$('.newSuiteDesc').get(0), function(counter) {
                    self.updateWordCount(140, counter.characters, 'description');
                });

                self.setupPagedList();        
                self.setupFieldEditors();                

            });
        },

        setupFieldEditors: function() {
            var self = this;
            var eds = this.editorEls;     

            for(var ed, i = 0, l = eds.length ; i < l ; i += 1) {
                ed = eds[i];
                self.suiteCreateEditors[ed] = new Underwood(self.$('.' + ed), {
                    toolbar: false,
                    disableReturn: true,   
                    spellcheck: false,                 
                    placeholder: {
                        hideOnClick: false,
                        text: ''
                    },                       
                });  
            }
        },

        destroyEditors: function() {
            var eds = this.editorEls;  
            for(var ed, i = 0, l = eds.length ; i < l ; i += 1) {
                ed = eds[i];
                this.suiteCreateEditors[ed] && this.suiteCreateEditors[ed].destroy();
            }
            this.suiteCreateEditors = void 0;
        },

        toggleSuitePrivacy: function(e) {
            var self = this;
            var $currentTarget = $(e.currentTarget);

            var makePublic = function() {
                self.$('.suitePrivacyOptions').addClass('public').removeClass('private');
                self.$('.publicOption').velocity('stop', true).velocity({ left: 0, opacity: 1 }, {
                  duration: 140
                });  
                self.$('.privateOption').velocity('stop', true).velocity({ left: 52, opacity: .2 }, {
                  duration: 140
                });                
            }
            var makePrivate = function() {
                self.$('.suitePrivacyOptions').addClass('private').removeClass('public');
                self.$('.publicOption').velocity('stop', true).velocity({ left: 58, opacity: .2 }, {
                  duration: 140
                });  
                self.$('.privateOption').velocity('stop', true).velocity({ left: 0, opacity: 1 }, {
                  duration: 140
                });                
            }

            if(this.privacySetting) {
                this.privacySetting = false;
                makePublic();
            } else {
                this.privacySetting = true;
                makePrivate();
            }
        },

        updateExclusionList: function(item, remove) {
            // item can be pk or (normalized) email address
            var remove = remove || false;
            if(remove) {
                var i = this.exclusionList.indexOf(item);
                if(i != -1) {
                    this.exclusionList.splice(i, 1);
                }
            } else {
                this.exclusionList.push(item);
            }           
        },

        setupPagedList: function() {
            var self = this;
            var $listViewEl = this.$('.suiteMemberSearch');
            var startPage = 1;
            var searchArr = window.location.search.split('=');
            var namedFilter = this.namedFilter || '';
            var loadFirstPage = true;
            if(searchArr.length >= 2 && searchArr[0] === '?page') {
                startPage = +searchArr[1];
            }
            var url = '/u/api/neighbours';

            this.clearViews(['suiteCreateList']);
            this.suiteCreateList = new PagedListView({
                firstPage: loadFirstPage,
                namedFilter: namedFilter,
                el: $listViewEl,
                url: url,
                templateName: 'user-invite-item',
                name: 'suitecreatelist'
            });
            this.listenTo(self.suiteCreateList, 'listViewFiltered', function(namedFilter) {
                namedFilter = namedFilter || '';
                // if(namedFilter=='suite') {
                //     this.suiteCreateList.templateName = 'suite-story-teaser';
                // } else if(namedFilter=='user') {
                //     this.suiteCreateList.templateName = 'user-teaser';
                // }
                self.suiteCreateList.fetch();
            });            
            this.listenToOnce(self.suiteCreateList, 'listViewReady', function() {
                self.suiteCreateList.fetch();
            });            
        },

        addMember: function(e) {
            console.log('adding member to array!');
            var $currentTarget = $(e.currentTarget);
            // var userEmail = $currentTarget.data('email');
            var userId = $currentTarget.data('pk');
            var newMember = this.suiteCreateList.collection.findWhere({id: userId }).toJSON();
            this.membersArray.unshift(newMember);
            this.resetSearchList();
        },

        resetSearchList: function() {
            this.$('.paginatedList').html('');
            this.$('.ctxtSearchInput').val('');
            this.chatCreateList && this.chatCreateList.destroy();
            this.renderInitialMembers();
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

        suiteCreateInputKeyup: function(e) {
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

        removeMemberFromList: function(e) {
            var $currentTarget = $(e.currentTarget);
            var item = $currentTarget.closest('.pendingMember');
            var itemId = item.data('pk') || item.data('email');

            item.remove();
            var i = this.membersArray.indexOf(itemId);
            if(i != -1) {
                this.membersArray.splice(i, 1);
            }
            self.updateExclusionList(itemId,true);
        },

        updateWordCount: function(limit, chars, field) {
            var remaining = limit - chars;
            if(field == 'description') {
                var container = $('.descCount');
            } else if(field == 'title') {
                var container = $('.titleCount');
            }
            container.html(remaining);
        },

        createIt: function(e) {
            var self = this;
            var $currentTarget = $(e.currentTarget);
            var $suiteTitle = this.$('.newSuiteTitle').text();
            var $suiteDesc = this.$('.newSuiteDesc').text();
            var membersArray = this.membersArray;
            var privacy = this.privacySetting;
            
            var $createNewSuite = $.ajax({
                url: '/s/api/new',
                type: 'POST',
                data: {
                    title: $suiteTitle,
                    desc: $suiteDesc,
                    members: JSON.stringify(membersArray),
                    private: privacy
                }
            });
            $createNewSuite.then(function(result) {
                self.exit();
                suiteio.vent.trigger('newSuite', result.suiteId);
                if(!self.options.addingTo) {
                    suiteio.pageController.loadSuite(result.hashedId, result.suiteId);
                }
            });
        },

        exit: function() {
            console.log('closing closeSuiteCreateModal');
            this.trigger('closeSuiteCreateModal');
        },

        clearViews: function(views) {
            views = views || ['suiteCreateList'];
            for(var view, i = 0, l = views.length ; i < l ; i += 1) {
                view = views[i];
                if(this[view]) {
                    this.stopListening(this[view]);
                    this[view].destroy();
                    this[view] = null;
                }
            }
        },

         destroy: function() {
            this.destroyEditors();
            Backbone.View.prototype.destroy.apply(this, arguments);
            this.$el.remove();
        }

    });
    return SuiteCreateView;
});


