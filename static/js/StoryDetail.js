//StoryDetail
define([
    'jquery',
    'backbone',
    'views/StoryView',
    'models/Story',
    'suiteio'
], function(
    $,
    Backbone,
    StoryView,
    Story,
    suiteio
    
) {
    'use strict';
    var StoryController = Backbone.View.extend({

        initialize: function(settings) {
            var model;
            this.settings = settings;
            this.id = 'StoryController';
            if(settings.json && typeof settings.json === 'object') {
                model = new Story.model(settings.json);
            } else if(settings.model){
                model = settings.model;
            } else {
                //no model specified...
            }
            suiteio.pageController.registerController(this);
            this.listenTo(suiteio.pageController, 'closeDown-StoryController', function() {
                this.clearAllMainViews();
            });

            if(model) {
                this.collection = new Story.collection([model]);
                this.loadStoryFromId(model.id);
            } else {
                this.collection = new Story.collection();
            }
           
        },

        loadStoryFromId: function(id, options) {
            var model = this.collection.get(id),
                _options = $.extend({}, options);
            if(!model || !model.get('resourceUri')) {
                //we don't have the model, so we needa grab it and then render
                model = model || new Story.model({'id': id});
                this.collection.add(model);
                _options.bootstrapped = false;
            } else if(model.get('modelIncomplete') && !$('#story-'+model.id).length) {
                //we have the model but it's incomplete and it hasn't been rendered
                _options.bootstrapped = false;
            } else {
                //we have the model and so it can be rendered if needed
                _options.bootstrapped = true;
            }
            this.loadStoryView(model, _options);
        },

        loadStoryFromModel: function(model, options) {
            var _options = $.extend({bootstrapped: true, forceRender: true}, options);
            this.collection.add(model);
            this.loadStoryView(model, _options);
            //assume it has NOT been rendered
        },

        loadStoryView: function(model, options) {
            var forceRender;
            this.clearAllMainViews();
            this.storyView = new StoryView({
                bootstrapped: options.bootstrapped,
                model: model,
                'edit': options.edit
            });
            forceRender = options.forceRender || this.storyView.needForceRender;//force a render if forceRender is true, or storyView's got no el

            this.currentActiveModel = model; //keep a reference to it so it can share it with others
            if(!options.bootstrapped) {
                //needs a fetch, wait for the new view to render, then trigger page change
                this.trigger('pageLoading');
                model.fetch();
                this.listenToOnce(this.storyView, 'renderComplete', function($el) {
                    this.updateMeta(model);
                    this.listenToOnce(suiteio.pageController, 'renderdone-'+this.id, function() {
                        this.storyView.afterRender();
                    });
                    this.trigger('pageChange', this, this.storyView.$el, model.get('absoluteUrl'), {
                        trigger: false,
                        keepHistory: {id: model.id}
                    });
                    if(options.edit) {
                        this.startEditMode(true, model);
                    }
                });
            } else if(forceRender) {
                //looks like we have the model but it's not rendered
                this.listenToOnce(this.storyView, 'renderComplete', function($el) {
                    options.forceRender = forceRender;
                    this.updateMeta(model);

                    this.listenToOnce(suiteio.pageController, 'renderdone-'+this.id, function() {
                        this.storyView.afterRender();
                    });
                    this.trigger('pageChange', this, this.storyView.$el, model.get('absoluteUrl'), {
                        trigger: false,
                        keepHistory: {id: model.id}
                    });
                });
                this.storyView.render();
            } else {
                options.bootstrapped = true;
                this.listenToOnce(suiteio.pageController, 'renderdone-'+this.id, function() {
                    this.storyView.afterRender();
                });
                //bootstrapped, we can trigger pagechange right away
                this.updateMeta(model);
                this.trigger('pageChange', this, this.storyView.$el, null, {
                    trigger: false,
                    keepHistory: {id: model.id}
                });
            }               
                      
        },

        updateMeta: function(storyModel) {
            var attrs = {};
            if(!storyModel) {
                attrs = {
                    'title': 'New Story',
                    'removeMeta': [{
                        'name': 'author'
                    }, {
                        'name': 'copyright'
                    }]
                };
            } else {
                attrs = {
                    'title': storyModel.get('title'),
                    'meta': [{
                        'name': 'author',
                        'content': storyModel.get('author').fullName
                    },{
                        'name': 'copyright',
                        'content': storyModel.get('author').fullName
                    }]
                };
                if (storyModel.get('bodyExcerptNoTags')) {
                    attrs.meta.push({
                        'name': 'description',
                        'content': storyModel.get('bodyExcerptNoTags')
                    });
                }
            }
            suiteio.metaHandler.updateHead(attrs);
        },

        clearAllMainViews: function() {
            var views = ['storyView'];
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
            this.clearAllMainViews();
        }
    });
    return StoryController;
});