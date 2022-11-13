define([
    'jquery',
    'underscore',
    'helpers/Lazyloader'
], function(
    $,
    _,
    LazyLoader
) {
    'use strict';
    var LazyLoaderJson = function(options) {
        this.options = _.extend({
            url: '.',
            delay: 200,
            dataType: 'json',
            id: new Date().getTime() + 'lazyloader'
        }, options);
        this.collection = this.options.collection;
        this.pageSize = options.pageSize || '';
        this.startingPageNo = this.getPageNo() + 1;
        this.suspended = false;
        this.reachedBottom = this.collection.bottomed || false;
        if(this.reachedBottom) {
            this.onReachedBottom();
            return;
        }
        this.started = false;
        this.pageCache = [];
        this.scrollWatch = this.options.scrollWatch || $(window);
    };
    //inheritance
    var Surrogate = function() {this.constructor = LazyLoaderJson; };
    Surrogate.prototype = LazyLoader.prototype;
    LazyLoaderJson.prototype = new Surrogate();

    //methods
    LazyLoaderJson.prototype.getNextPage = function() {
        if(this.reachedBottom) {
            return;
        } 
        // var currentPage = this.getPageNo(),
            // nextPage = currentPage + 1,
        var self = this;
        this.incrementPageNo();

        return this.collection.fetch({
            reset: false,
            remove: false,
            data: this.options.data || null,
            success: function(collection, response) {
                if(!self.pageCache) {
                    //lazyloader destroyed, just return
                    return;
                }
                self.pageCache.push(response);

                // if(response.bottomed) {
                //     console.log('hey - says here we are bottomed');
                //     self.reachedBottom = true;
                //     self.onReachedBottom();
                //     collection.bottomed = true;
                // } 

                // if(self.options.tastypie || collection.tastypie) {
                //     //for the tastypie paged api, it will never get to a 404 page
                //     //we declare "bottomed" when next is null, so we don't loop forever and ever
                //     if(!collection.nextUrl) {
                //         console.log('no next url -  bottomed!');
                //         self.reachedBottom = true;
                //         self.onReachedBottom();
                //         collection.bottomed = true;
                //     } else {
                //         console.log('oh, we have a next url - not bottomed');
                //     }
                // }
                // if(response.objects && !response.objects.length) {
                //     self.reachedBottom = true;
                //     self.onReachedBottom();
                //     collection.bottomed = true;
                // }
                if(self.options.success && typeof self.options.success === 'function') {
                    self.options.success.apply(self, arguments);
                }
            },
            error: function() {
                // if 404
                self.reachedBottom = true;
                self.onReachedBottom();
                if(self.options.error && typeof self.options.error === 'function') {
                    self.options.error.apply(self, arguments);
                }
            }
        });
    };

    LazyLoaderJson.prototype.kickOff = function() {
        //kick off the lazy loader getpage cycle
        this.started = true;
        this.bindScroll();
        return this.getNextPage();
    };

    LazyLoaderJson.prototype.getPageNo = function() {
        return this.collection.getCurrentPageNo();
    };

    LazyLoaderJson.prototype.incrementPageNo = function() {
        this.collection.incrementPageNo();
    };

    return LazyLoaderJson;
});