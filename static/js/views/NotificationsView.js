// NotificationsView
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
    var NotificationsView = Backbone.View.extend({
        events: function() {
            return _.extend({
                // 'click .toggleNotifSend': 'toggleAccrualNotify'
                'click .acceptRejectInvite': 'suiteInviteAcceptReject',
                'show.bs.tab .notifTab[data-toggle="tab"]': 'tabChange'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function () {
            var self = this;
            this.notifsTmplPromise = suiteio.templateLoader.getTemplate('notifications-detail', ['notification']);
            this.feedType = 'all'
            this.urlRoot = '/notifications';
            var $el = $('#notifications-view');
            if($el.length) {
                this.setElement($el);
                this.startNotifsPaginator();
                this.trigger('renderComplete', this.$el);
            } else {
                // this.render();
            }
        },

        fetchContext: function() {
            var self = this;
            return $.ajax({
                url: '/notifications/',
                type: 'GET',
                data: {
                    feedtype: self.feedType,
                    spa: true
                }
            });
        },

        render: function() {
            var self = this;
            var $el;
            var $html;
            this.fetchContext().then(function(context) {
                self.notifsTmplPromise.done(function(tmpl) {
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
                    self.trigger('renderComplete', self.$el);
                });      
            });
        },

        afterRender: function() {
            suiteio.checkUnread();
            this.startNotifsPaginator();
        },

        startNotifsPaginator: function(fetchFirst) {
            fetchFirst = fetchFirst || false;
            var self = this;
            var url = this.urlRoot;
            switch(this.feedType) {
                case 'msgs':
                    var $listViewEl = this.$('.msgNotifs');
                break;
                case 'mod':
                    var $listViewEl = this.$('.modNotifs');
                break;                
                default:
                    var $listViewEl = this.$('.allNotifs');
                break;                
            }
            this.myNotifsListView && this.myNotifsListView.destroy();
            this.myNotifsListView = new PagedListView({
                el: $listViewEl,
                firstPage: fetchFirst,
                url: url,
                templateName: 'notification',
                name: 'mynotifs'
            });
            self.listenToOnce(self.myNotifsListView, 'listViewReady', function() {
                self.myNotifsListView.fetch();
            });
            self.listenToOnce(self.myNotifsListView, 'errorFetchingCollection' || 'noListViewResults', function() {
                console.log('no, nothing, none');
                var memberName = suiteio.loggedInUser.get('firstName') || suiteio.loggedInUser.get('fullName') || 'you who cannot be named';
                self.$('.allNotifs .paginatedList').html('<div class="centered no-notifs noNotifs">Good news and bad news, ' + memberName + '. You have no new notifications to deal with.');
            });
        },

        tabChange: function(e) {
            var tab = $(e.currentTarget).data('target');
            this.feedType = tab.replace('#', '').split('-')[0];
            console.log('feedtype? ' + this.feedType);
            this.render();
        },

        clearNotification: function(e) {
            var self = this,
                $parent = $(e.currentTarget).closest('.notifItem'),
                key = $parent.data('key'),
                score = $parent.data('score');
            $.ajax({
                url: '/notifications',
                type: 'POST',
                data: {
                    clearnotif: true,
                    key: key,
                    score: score
                },
                success: function() {
                    $parent.remove();
                }
            });
        },

        suiteInviteAcceptReject: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            var parent = $target.closest('.notifItem');
            var thanksMsg = '<p class="thanks-response">Done!</p>';    
            var accept = $(e.currentTarget).data('accept');
            var suite = $(e.currentTarget).data('suite');
            suiteio.acceptSuiteInvite(suite, accept);
            self.listenToOnce(suiteio.vent, 'suiteInviteAccepted', function(status) {
                parent.html(thanksMsg);
                 var wait = setTimeout(function() { 
                        parent.remove();
                 }, 2000);
            });
        },

        updateSuiteRequestStatus: function(e) {
            var $target = $(e.currentTarget),
                requestId = $target.data('id'),
                status = $target.data('status'),    
                url = '/s/api/request_action/' + requestId;

            $.ajax({
                url: url,
                type: 'POST',
                data: {
                    stat: status = status
                },
                success: function() {
                    var thanksMsg = '<p class="thanks-response">Done! You can view your old notifications by clicking the <strong>READ</strong> tab above</p>',
                        parent = $target.closest('li');
                        parent.html(thanksMsg);

                         var wait = setTimeout(function() { 
                            parent.remove();
                     }, 3000);
                }
            });
        },

        clearSupplementalViews: function() {
            var views = ['myNotifsListView'];
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
            this.clearSupplementalViews();
            this.trigger('clearReadNotifs');
            Backbone.View.prototype.destroy.apply(this, arguments);
        }


    });
    return NotificationsView;
});