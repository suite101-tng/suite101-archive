//PagingCollection
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
    var PagingCollection = {};
    PagingCollection.collection = Backbone.Collection.extend({

        model: Backbone.Model,

        initialize: function(data, options) {
            var _options = options || {};
            this.options = _options;
            if(_options.urlRoot) {
                this.urlRoot = _options.urlRoot;
            }
            if(_options.nextUrl) {
                this.nextUrl = _options.nextUrl;
            }
            this.tastypie = _options.tastypie;
            this.skipFirst = _options.skipFirst || 0;
            this.currentPageNo = _options.startPage || 0;
            this.limit = _options.pageSize || 15;
            this.bottomed = !!_options.bottomed;
        },

        getModelsAtPage: function(pageNo) {
            if(pageNo === undefined) {
                pageNo = this.currentPageNo;
            }
            var start = pageNo * this.limit;
            var end = start + this.limit;
            if(this.skipFirst && !pageNo > 1) {
                start = start + this.skipFirst;
            }
            return this.slice(start, end);
        },

        getJSONAtPage: function(pageNo) {
            if(pageNo === undefined) {
                pageNo = this.currentPageNo;
            }
            var models = this.getModelsAtPage(pageNo);
            return _(models).map(function(model) {
                return model.toJSON();
            });
        },

        getLastPageNo: function() {
            return (this.length / this.limit) - 1
        },

        url: function() {
            var returnUrl = this.urlRoot, querySym, offset=0;
            if(this.nextUrl) {
                returnUrl = this.nextUrl;
            } else if(this.tastypie) {
                offset = (this.currentPageNo===0) ? 0 : (this.currentPageNo)* this.limit;
                querySym = (returnUrl.indexOf('?') > -1)? '&' : '?';
                returnUrl = returnUrl + querySym + 'limit=' + this.limit + '&offset=' +  offset ;
            } else if(this.currentPageNo > 0 && !this.bottomed) {
                querySym = '?';
                if(returnUrl.indexOf('?') && returnUrl.indexOf('?') > -1) {
                    querySym = '&';
                }
                returnUrl = returnUrl + querySym + 'page=' + (this.currentPageNo);
            }
            return returnUrl;
        },

        allReset: function(options) {
            var _options = _.extend({reset: true}, options);
            this.currentPageNo = 0;
            this.bottomed = false;
            return this.fetch(_options);
        },

        getCurrentPageNo: function() {
            return this.currentPageNo;
        },

        incrementPageNo: function() {
            ++this.currentPageNo;
        },

        parse: function(attr) {
            var objects = attr;
            if(attr.meta) {
                this.nextUrl = attr.meta.next;
                this.prevUrl = attr.meta.previous;
                this.limit = attr.meta.limit;
                this.offset = attr.meta.offset;
                this.totalCount = attr.meta.totalCount;
                if(!attr.meta.next) {
                    this.bottomed = true;
                }
                if(!this.offset) {
                    this.currentPageNo = 1;
                } else {
                    this.currentPageNo = this.offset / this.limit;
                }
            }
            if(attr.objects) {
                objects = attr.objects;
            } else {
                return attr;
            }
            return objects;
        }

    });
    return PagingCollection;
});