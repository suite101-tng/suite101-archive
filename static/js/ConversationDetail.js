// ConversationController
define([
    'jquery',
    'backbone',
    'suiteio',
    'models/Conversation',
    'views/ConversationView',
    'views/PostCreateView',
    'views/PostEditView',
    'main/AdsManager',
], function(
    $,
    Backbone,
    suiteio,
    Conversation,
    ConversationView,
    PostCreateView,
    PostEditView,
    AdsManager
) {
    'use strict';
    var ConversationController = Backbone.View.extend({

        initialize: function(options) {
            var model;
            this.options = options;
            this.id = 'ConversationController';

            suiteio.pageController.registerController(this);
            suiteio.pageController.registerEventBroadcast([
                ///////
            ], this);
            this.listenTo(suiteio.pageController, 'closeDown-ConversationController', function() {
                this.clearViews();
            });
            // this.listenToOnce()
        },

        updateMeta: function(convModel) {
            var attrs = {};
            if(!convModel) {
                attrs = {
                    'title': 'External Link',
                    'removeMeta': [{
                        'name': 'author'
                    },
                    {
                        'name': 'copyright'
                    }]
                };
            } else {
                attrs = {
                    'title': 'just a test title',
                    'meta': [{
                        'name': 'owner',
                        'content': ''
                    }]
                };
            }
            suiteio.metaHandler.updateHead(attrs);
        },

        loadConvFromModel: function(bootstrappedModel) {
            var convModel = new Conversation.model(bootstrappedModel);
            this.loadConvView({ model: convModel, skipRender: true });

        },

        loadConvFromId: function(options) {
            var self = this;
            var convModel;
            var convId = options.convId || '';
            convModel = new Conversation.model({id: convId});
            convModel.fetch().done(function(model) {
                self.loadConvView({ model: convModel });
            });   
        },

        loadConvView: function(options) {
            var self = this;
            options = options || {};
            var skipRender = options.skipRender || false;

            // var metaAttrs = {
            //     title: title,
            //     meta: [{
            //         'name': 'description',
            //         'content': title
            //     }]
            // };               

            this.clearViews();
            this.convView = new ConversationView(options);

            this.listenTo(this.convView, 'setupMainPostForm', function($el, conv) {
                self.startPostCreate($el, true, conv);
            });

            this.listenTo(this.convView, 'unsetMainPostForm', function() {
                console.log('stopping main-form create mode...');
            });

            this.listenToOnce(this.convView, 'renderComplete', function($el) {
                console.log('render is complete');
                // this.setupStorySupplementaryViews();
                // this.updateMeta();

                self.listenToOnce(suiteio.pageController, 'renderdone-'+self.id, function() {
                    self.convView.afterRender();
                });

                self.trigger('pageChange', self, self.convView.$el, '', {
                    trigger: false
                });
            });
            if(!skipRender) {
                this.convView.render();
            }

        },

        startPostCreate: function($el, mainForm, convModel) {
            var self = this;

            // TODO: is the user allowed to post?

            var model = new Conversation.postModel({author: suiteio.loggedInUser.toJSON(), conversation: convModel.toJSON()});
            self.postCreateView = new PostCreateView({
                el: $el,
                model: model
            });           
            if(!mainForm) {
                this.postCreateView.render();    
            } else {
                this.postCreateView.setupEdit();
            }

            this.listenTo(this.postCreateView, 'addPost', function(postModel) {
                convModel.postsCollection.create(postModel);
            });            
            
        },

        // inlineStoryCreate: function(options) {
        //     var self = this;
        //     var parentId = options.parentId;
        //     var parentType = options.parentType;
        //     console.log('create a new inline story!');
        //     var $el = options.el;
        //     var onMain = options.onMain;

        //     console.log('this.inlineCreateActive: ' + this.inlineCreateActive);

        //     if(this.inlineCreateActive) {
        //         console.log('close active editor please');
        //         this.storyInlineCreateView.toggleEditAction();
        //         return;
        //     } 
        //     var model = new Story.model({author: suiteio.loggedInUser.toJSON(), storyParent: { pk: parentId, objType: parentType }});
        //     this.storyInlineCreateView = new StoryInlineCreateView({
        //         el: $el,
        //         model: model,
        //         onMain: onMain
        //     });
        //     this.listenTo(this.storyInlineCreateView, 'inlineCreateStarted', function() {
        //         self.inlineCreateActive = true;
        //         console.log('------------------- inlinecreate started!');
        //     });
        //     this.listenToOnce(this.storyInlineCreateView, 'stopInlineCreate', function() {
        //         self.inlineCreateActive = false;
        //         console.log('------------------- OK TO CLOSE INLINE CREATE!');
        //     });
            
        //     this.storyInlineCreateView.render();              
        // },


        startPostEditMode: function(model) {
            // if(this.deviceNotSupported()) {
            //     return;
            // }
            if(suiteio.loggedInUser.id !== model.get('author').id && !suiteio.loggedInUser.get('isStaff') && !suiteio.loggedInUser.get('isModerator')) {
                //not the owner, nor mod, nor staffer
                return;
            }
            // this.clearAllMainViews();
            this.postEditView = new PostEditView({
                bootstrapped: bootstrapped,
                model: model
            });
            this.listenToOnce(suiteio.pageController, 'pageChanging-'+this.id, function() {
                if(this.postEditView) {
                    this.postEditView.endEdit({revert: true});
                }
            });
            this.listenToOnce(this.postEditView, 'doneEditMode', this.endEditMode);
            this.trigger('startEditing');
        },

        endPostEditMode: function(model) {
            this.clearAllMainViews();
            if(model) {
                this.trigger('editedStory', model);
                this.loadStoryView(model, {bootstrapped: true, forceRender: true, skipReadTracker: true});
            }
            this.trigger('doneEditing');
            this.loadStoryFromModel(model);
            if(this.storyView){
                this.storyView.editing = false;
            }
        },

        setupConvSupplementaryViews: function(model, options) {
            var _options = options || {};
            if(this.readTrackerView) { this.readTrackerView.destroy(); this.readTrackerView = null;}
            if(model) {
                this.listenToOnce(suiteio.pageController, 'renderdone-'+this.id, function() {
                    this.setupAds(model, _options.bootstrapped, _options.forceRender);
                    this.setupReadTracker(model, _options);
                });
            }
        },

        setupAds: function(model, bootstrapped, forceRender) {
            AdsManager.destroy();
            if(model.get('adsEnabled')) {
              
                if(!suiteio.loggedInUser) {
                    AdsManager.initialize({
                        el: this.storyView.el
                    });
                    // AdsManager.loadDfp();
                    AdsManager.loadContentAd();
                    if(!bootstrapped || forceRender) {
                        AdsManager.loadAdsense();
                    }
                }
            }
        },        

        clearViews: function(views) {
            views = views || ['convView', 'convCreateView'];
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
            suiteio.pageController.unregisterRouter(this);
            this.stopListening();
            this.clearViews();
            // if (this.readTrackerView) {
            //     this.readTrackerView.destroy();
            // }            
        }
    });

    return ConversationController;
});