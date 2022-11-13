//Story
define([
    'jquery',
    'underscore',
    'backbone',
    'models/PagingCollection'
], function(
    $,
    _,
    Backbone,
    PagingCollection
) {
    'use strict';
    var StoryModel = Backbone.Model.extend({
        
        urlRoot: '/api/v1/story/',
        
        defaults: {
            suites: [],
            wordsChanged: 0,
            otherSuitesCount: 0,
            title: '',
            subtitle: '',
            tag_list: [],
            body: '',
            storyParent: ''
        },
        
        url: function() {
            if(this.get('resourceUri')) {
                return this.get('resourceUri');
            } else if(this.id) {
                return this.urlRoot + this.id + '/';
            } else {
                return this.urlRoot;
            }
        },
        
        initialize: function(initialData) {
            this.processAttributes(initialData, true);
            this.listenToOnce(this, 'sync', function() {
            });
        },
                        
        processAttributes: function(attrs, doSet) {
            var data = _.extend({}, attrs);
                     
            if(doSet) {
                this.set({
                    publish: data.publish
                }, {silent: true});
            }
            return data;
        },
        
        parse: function(response) {
            //this is only called when the data is coming in from the server through a fetch or save
            this.set({modelIncomplete: false}, {silent: true});
            return this.processAttributes(response);
        },
        
        validate: function (attrs) {
            // if (!attrs.title) {
            //     return 'Please give your story a title.';
            // }
            // if (!attrs.body) {
            //     return 'Your story wasn\'t saved because it\'s missing a body!';
            // }
        }
    });
    var StoryCollection = PagingCollection.collection.extend({
        
        model: StoryModel,
        
        urlRoot: '/api/v1/story/',

        tastypie: true
    });
    return {
        model: StoryModel,
        collection: StoryCollection
    };
});