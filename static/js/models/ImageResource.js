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
    var ImageResource = {};
    ImageResource.model = Backbone.Model.extend({
        defaults: {
            'caption': '',
            'credit': '',
            'creditLink': '',
            'origImageUrl': ''
        },
        checkLink: function(text) {
            if(!text) { return false; }
            var urlRegex = new RegExp(/^(https?:\/\/)([\da-z\.-]+)\.([a-z\.]{2,6})([!#\/\w \.\~\(\)-]*)*\/?(\?[=&\w\.-]*)?$/ig);
            if(!text.match(urlRegex)) {
                text = 'http://' + text;
                if(!text.match(urlRegex)) { return false; }
            }
            return text;
        },
        validate: function(attrs) {
            var creditIsLink = this.checkLink(attrs.credit),
                creditLink = this.checkLink(attrs.creditLink);
            if(creditLink) {
                this.set({creditLink: creditLink}, {silent: true});
            } else if(creditIsLink) {
                //creditlink is empty, credit is of a link form
                //put credit into creditLink field, empty credit field
                this.set({
                    creditLink: creditIsLink,
                    credit: ''
                });
            }
        },
        urlRoot: '',
        url: function() {
            return this.urlRoot + this.id + '/';
        }
    });
    ImageResource.collection = Backbone.Collection.extend({
        model: ImageResource.model
    });
    return ImageResource;
});