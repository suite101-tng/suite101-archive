//Link
define([
    'jquery',
    'underscore',
    'backbone'
], function(
    $,
    _,
    Backbone
) {
    'use strict';
    
    var LinkModel = Backbone.Model.extend({
        
        urlRoot: '/api/v1/link/',
        
        defaults: {
            title: '',
            description: '',
            htmlObject: '',
            provider: '',
            tag_list: []
        },
        
        url: function() {
            console.log(this);
            if(this.get('resourceUri')) {
                return this.get('resourceUri');
            } else if(this.id) {
                console.log('we have an id: ' + this.id);
                return this.urlRoot + this.id + '/';
            } else {
                return this.urlRoot;
            }
        },
        
        initialize: function(initialData) {
            console.log('init link model...');
            this.processAttributes(initialData, true);
        },
                        
        processAttributes: function(attrs, doSet) {
            var data = _.extend({}, attrs);
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
    var LinkCollection = Backbone.Collection.extend({});
    return {
        model: LinkModel,
        collection: LinkCollection
    };
});