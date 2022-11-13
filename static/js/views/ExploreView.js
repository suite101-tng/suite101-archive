//ExploreView
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'views/PagedListView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    PagedListView
) {
    'use strict';
    var ExploreView = Backbone.View.extend({
        events: function() {
            return _.extend({
                    'click .exploreTab': 'selectExploreTab',
                    'submit .searchForm': 'exploreSearchSubmit',
                    'click .focusExploreSearch': 'focusExploreSearch',
                    'click .storyTeaserBody': 'toggleFullTeaser'
                }, _.result(Backbone.View.prototype, 'events')
            );
        },

        initialize: function (options) {
            var self = this;
            var contentTemplate;
            options = options || {};
            this.viewType = options.viewType || '';
            this.urlRoot = '/' + this.viewType;

            this.exploreTmplPromise = suiteio.templateLoader.getTemplate('explore-shell', ['story-teaser', 'suite-teaser', 'user-teaser', 'tag-list-item']);

            var $el = $('#explore-' + this.viewType);
            // $el.find('.tip').tooltip('destroy').tooltip();
            if($el.length) {
                this.setElement($el);
                this.trigger('renderComplete', $el, this.viewType);
                this.startExplorePaginator();
            } else {
                // this.render();
            }
        },

        fetchContext: function() {
            var self = this;
            return $.ajax({
                url: self.urlRoot,
                type: 'GET',
                data: {
                    spa: true,
                    viewtype: self.viewType
                }
            });
        },

        render: function() {
            var self = this;
            var $el;
            var $html;
            this.fetchContext().then(function(context) {
                self.exploreTmplPromise.done(function(tmpl) {
                    $html = $(tmpl(context));
                    if($html.length > 1) {
                        $el = $('<div/>').append($html);
                    } else {
                        $el = $html.eq(0);
                    }
                    if(self.$el.is(':empty')) {
                        //first time render
                        self.setElement($el);
                    } else {
                        self.$el.html($html.html());
                    }
                    self.trigger('renderComplete', self.$el, self.viewType);
                    self.startExplorePaginator();
                });      
            });
        },

        startExplorePaginator: function(fetchFirst) {
            fetchFirst = fetchFirst || false;
            var self = this;
            var url = this.urlRoot;
            var threshold = 130;
            var $listViewEl, contentTemplate = 'story-teaser';
            switch(this.viewType) {
                case 'long':
                    url = '/long',
                    $listViewEl = $('.exploreLongReads');
                break;
                case 'latest':
                    url = '/latest',
                    $listViewEl = $('.exploreLatestStories');
                break;
                case 'top':
                    url = '/top',
                    $listViewEl = $('.explorePopularStories');
                break;
                case 'discussed':
                    url = '/discussed',
                    $listViewEl = $('.exploreDiscussedtStories');
                break;                
                case 'explore':
                    url = '/explore',
                    $listViewEl = self.$('.exploreMainLatestStories');
                break;
            }

            this.exploreListView && this.exploreListView.destroy();
            this.exploreListView = new PagedListView({
                el: $listViewEl,
                firstPage: fetchFirst,
                threshold: threshold,
                url: url,
                templateName: contentTemplate,
                name: 'explore-' + self.viewType
            });
            self.listenToOnce(self.exploreListView, 'listViewReady', function() {
                self.exploreListView.fetch();
            }); 
            self.listenToOnce(self.exploreListView, 'errorFetchingCollection' || 'noListViewResults', function() {
                // var memberName = suiteio.loggedInUser.get('firstName') || suiteio.loggedInUser.get('fullName') || 'you who cannot be named';
                // self.$('.unreadNotifs .paginatedList').html('<div class="no-notifs noNotifs">Good news and bad news, ' + memberName + '. You have no new notifications to deal with.');
            });
        },

        exploreSearchSubmit: function(e) {
            console.log('got a query...');
            e.preventDefault();
            var query = this.$('.exploreSearchTerm').val() || '';
            query = query.toLowerCase().replace(/\s\s+/g, ' ').replace(/[^a-z\d\s]+/gi, "").trim().replace(/\s/ig, '-');
            if(query) {
                this.trigger('exploreSearchQuery', query);
            } 
        },

        selectExploreTab: function(e) {
            var newTab = $(e.currentTarget).data('tab');
            this.trigger('changeExploreTab', newTab);
        },

        focusExploreSearch: function(e) {
            this.$('.exploreSearchTerm').focus();
        },

        toggleFullTeaser: function(e) {
            suiteio.toggleFullTeaser(e);
        },
        
        modAction: function(e) {
            suiteio.pageController.modThis(e);
        },
        
        openSuiteSelector: function(e) {
            suiteio.openSuiteSelector(e);
        },

        respondTo: function(e) {
            suiteio.respondTo(e);
        },

        followSuite: function(e) {
            suiteio.followSuite(e);
        },

        followUser: function(e) {
            suiteio.followUser(e);
        },

        destroy: function() {
            this.exploreListView && this.exploreListView.destroy();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }
    });

    return ExploreView;
});