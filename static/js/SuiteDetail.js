define([
    'jquery',
    'backbone',
    'underscore',
    'views/SuiteView',
    'views/SuiteEditView',
    'views/SuiteCreateView',
    'models/Suite',
    'views/ModerateView',
    'suiteio'
], function(
    $,
    Backbone,
    _,
    SuiteView,
    SuiteEditView,
    SuiteCreateView,
    Suite,
    ModerateView,
    suiteio
) {
    'use strict';
    var SuiteController = Backbone.View.extend({
        initialize: function(options) {
            var model;
            this.options = options;
            this.id = 'SuiteController';
            if(options.json && typeof options.json === 'object') {
                model = new Suite.model(options.json);
            } else if(options.model) {
                model = options.model;
            } else {
                //no model...
            }
            this.forceRender = {}; //flag to force a view rerender
            //register itself, so pageController listen to it for page render events
        
            suiteio.pageController.registerController(this);
            suiteio.pageController.registerEventBroadcast([
                'startEditing',
                'doneEditing'
            ], this);

            this.listenTo(suiteio.pageController, 'closeDown-SuiteController', function() {
                this.clearAllMainViews();
            });

            this.listenTo(suiteio.pageController, 'createdStory editedStory', function(changedModel, isPublished) {
                if(isPublished || changedModel.get('isPublished')) {
                    //we don't care if it's not published
                    var suites = changedModel.get('suites'),
                        featuredSuite = changedModel.get('featuredSuite'),
                        model;
                    if(featuredSuite && featuredSuite.id) {
                        model = this.collection.get(featuredSuite.id);
                        if (model) {
                            //new story created has this suite as its featuredSuite
                            this.forceRender[featuredSuite.id] = true;
                            model.fetch();
                        }
                    } else if(suites && suites.length) {
                        for(var i=0, suite, l=suites.length ; i<l ; ++i) {
                            suite = suites[i];
                            model = this.collection.get(suite.id);
                            if(model) {
                                this.forceRender[model.id] = true;
                                model.fetch();
                                break;
                            }
                        }
                    }
                }
            });
            this.collection = new Suite.collection();
            if(model) {
                this.collection.add(model);
                this.loadSuiteFromId(model.id, {startPage: options.startPage});
            } else {

            }
        },
        

        
        isDirty: function() {
            if(this.createView) {
                return this.createView.isDirty();
            } else if (this.suiteEditView) {
                return this.suiteEditView.isDirty();
            } else {
                return false;
            }
        },
        
        loadSuiteFromModel: function(model, options) {
            var _options = $.extend({bootstrapped: true, forceRender: true}, options);
            this.collection.add(model);
            this.loadSuiteView(model, _options);
        },
        
        loadSuiteFromSlug: function(slug) {
            var model = this.collection.findWhere({slug: slug}),
                _options = {
                    bootstrapped: true
                };
            if(!model || !model.id) {
                model = model || new Suite.model({slug: slug});
                this.collection.add(model);
                _options.bootstrapped = false;
            } else if(model.get('modelIncomplete') && !$('#suite-'+model.id).length) {
                _options.bootstrapped = false;
            } else {
                //nop
            }
            this.loadSuiteView(model, _options);
        },
        
        loadSuiteFromId: function(id, options) {
            options = options || {};
            var model = this.collection.get(id),
                _options = _.extend(options, {
                    bootstrapped: true
                });
            if(!model || !model.get('resourceUri')) {
                model = new Suite.model({id: id});
                this.collection.add(model);
                _options.bootstrapped = false;
            } else if(model.get('modelIncomplete') && !$('#suite-'+model.id).length) {
                _options.bootstrapped = false;
            } else {
                //nop
            }
            this.loadSuiteView(model, _options);
        },

        loadSuiteView: function(model, options) {
            var forceRender,
                pageAnimation;
            this.clearAllMainViews();
            this.suiteView = new SuiteView({
                bootstrapped: options.bootstrapped,
                model: model
            });
            this.listenTo(this.suiteView, 'goToStoryFromSuite', function(slug, href) {
                suiteio.pageController.navigate(href, {trigger: true});
            });
            this.listenTo(this.suiteView, 'openEditMode', function(model) {
                this.startEditing(true, model);
            });
            this.listenTo(this.suiteView, 'editAboutMode', function(model) {
                this.startAboutEdit(true, model);
            });
            forceRender = options.forceRender || this.suiteView.needForceRender;//force a render if forceRender is true, or suiteView's got no el
            this.currentActiveModel = model; //keep a reference to it so it can share it with others
            
            if(!options.bootstrapped) {
                //needs a fetch, wait for the new view to render, then trigger page change
                this.trigger('pageLoading');
                model.fetch();
                this.listenToOnce(this.suiteView, 'renderComplete', function($el) {
                    this.setupSuiteSupplementaryViews(model, options);
                    this.updateMeta(model);
                    this.listenToOnce(suiteio.pageController, 'renderdone-'+this.id, function() {
                        this.suiteView.afterRender();
                    });
                    this.trigger('pageChange', this, this.suiteView.$el, model.get('absoluteUrl'), {
                        trigger: false,
                        keepHistory: {id: model.id}
                    });
                });
            } else if(forceRender) {
                //looks like we have the model but it's not rendered
                this.listenToOnce(this.suiteView, 'renderComplete', function($el) {
                    options.forceRender = forceRender;
                    this.setupSuiteSupplementaryViews(model, options);
                    this.updateMeta(model);

                    this.listenToOnce(suiteio.pageController, 'renderdone-'+this.id, function() {
                        this.suiteView.afterRender();
                    });
                    this.trigger('pageChange', this, this.suiteView.$el, model.get('absoluteUrl'), {
                        trigger: false,
                        keepHistory: {id: model.id}
                    });
                });
                this.suiteView.render();
            } else {
                options.bootstrapped = true;
                this.setupSuiteSupplementaryViews(model, options);
                this.listenToOnce(suiteio.pageController, 'renderdone-'+this.id, function() {
                    this.suiteView.afterRender();
                });
                //bootstrapped, we can trigger pagechange right away
                this.updateMeta(model);
                this.trigger('pageChange', this, this.suiteView.$el, null, {
                    trigger: false,
                    keepHistory: {id: model.id}
                });
            }
        },

        startEditing: function(bootstrapped, model) {
            if(!model.get('edViewing')) {
                return;
            }
            if(this.suiteView) {
                this.suiteView.destroy();
                this.suiteView = null;
            }
            if(this.suiteEditView) {
                this.suiteEditView.destroy();
                this.suiteEditView = null;
            }
            this.suiteEditView = new SuiteEditView({
                bootstrapped: bootstrapped,
                model: model
            });
            this.listenToOnce(this.suiteEditView, 'doneEditMode', this.endEditMode);
            this.trigger('startEditing');
        },

        endEditMode: function(model) {
            this.suiteEditView && this.suiteEditView.destroy();
            this.suiteEditView = null;
            if(model) {
                this.loadSuiteView(model, {bootstrapped: true, forceRender: true});
            }
            this.trigger('doneEditing');
        },
        
        createSuite: function() {
            var model = new Suite.model({owner: suiteio.loggedInUser.toJSON()});
            this.createView = new SuiteCreateView({model: model});
            this.listenToOnce(this.createView, 'renderComplete', function($el) {
                this.createViewRenderComplete($el);
            });
            this.listenToOnce(this.createView, 'doneCreate', function(model) {
                this.loadSuiteFromModel(model);
                this.createView.destroy();
                this.createView = null;
            });
            // this.listenToOnce(this.createView, 'endCreate', function() {
            //     //just ends, be it canceled or interrupted or after a create is done, this hits
            //     this.createView = null;
            // });
            this.createView.render();
        },
        
        createViewRenderComplete: function($el) {
            this.listenToOnce(suiteio.pageController, 'renderdone-'+this.id, function($el) {
                this.createView.afterRender();
            });
            this.updateMeta();
            this.trigger('pageChange', this, $el, '/s/new', {trigger: false, doNotTrack: true});
        },

        setupSuiteSupplementaryViews: function(model, options) {
            var _options = options || {};
            if(this.moderateView) { this.moderateView.destroy(); this.moderateView = null;}
            if(model) {
                if(suiteio.loggedInUser && suiteio.loggedInUser.get('isModerator') === true) {
                    this.moderateView = new ModerateView({
                        el: this.suiteView.el,
                        suiteId: model.id
                    });
                }
            }
        },
        
        updateMeta: function(suiteModel) {
            var attrs = {};
            if(!suiteModel) {
                attrs = {
                    'title': 'New Story',
                    'removeMeta': [{
                        'name': 'author'
                    },
                    {
                        'name': 'copyright'
                    }]
                };
            } else {
                attrs = {
                    'title': suiteModel.get('name'),
                    'meta': [{
                        'name': 'author',
                        'content': suiteModel.get('owner').fullName
                    },
                    {
                        'name': 'copyright',
                        'content': suiteModel.get('owner').fullName
                    }]
                };
            }
            suiteio.metaHandler.updateHead(attrs);
        },

        clearAllMainViews: function() {
            var views = ['suiteView', 'suiteEditView'];
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
        }

    });
    return SuiteController;
});