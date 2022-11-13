// PostEmbedResource
define([
    'jquery',
    'underscore',
    'backbone',
], function(
    $,
    _,
    Backbone
) {
    'use strict';
    var PostEmbedResource = {};
    PostEmbedResource.model = Backbone.Model.extend({
        defaults: {
            'embedType': '',
            'embedObject': '',
            'caption': '',
            'spill': '',
            'cover': ''
        },
        urlRoot: '',
        url: function() {
            console.log(this.urlRoot + this.id + '/');
            return this.urlRoot + this.id + '/';
        }
    });
    PostEmbedResource.collection = Backbone.Collection.extend({
        model: PostEmbedResource.model
    });
    return PostEmbedResource;
});