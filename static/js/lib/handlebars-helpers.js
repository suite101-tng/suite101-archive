define(['lib/handlebars', 'suiteio'], function(Handlebars, suiteio) {
    'use strict';
    
    Handlebars.registerHelper('pluralize', function(number, single, plural) {
        if (number === 1) { return single; }
        else { return plural; }
    });

    Handlebars.registerHelper ('truncate', function (str, len) {
        var str = str || '';
        if (str.length > len && str.length > 0) {
            var new_str = str + " ";
            new_str = str.substr (0, len);
            new_str = str.substr (0, new_str.lastIndexOf(" "));
            new_str = (new_str.length > 0) ? new_str : str.substr (0, len);

            return new Handlebars.SafeString ( new_str +'...' ); 
        }
        return str;
    });

    Handlebars.registerHelper ('ordinalize', function (value) {
      var __indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; },
        normal, _ref;
      value = parseFloat(value);
      normal = Math.abs(Math.round(value));
      if (_ref = normal % 100, __indexOf.call([11, 12, 13], _ref) >= 0) {
        return "" + value + "th";
      } else {
        switch (normal % 10) {
          case 1:
            return "" + value + "st";
          case 2:
            return "" + value + "nd";
          case 3:
            return "" + value + "rd";
          default:
            return "" + value + "th";
        }
      }
    }, 'number');


    Handlebars.registerHelper ('shortTime', function (time) {

      if(!time) {
        return '--'
      }

      var units = [
        { name: "min", limit: 3600, in_seconds: 60 },
        { name: "hr", limit: 86400, in_seconds: 3600  }
      ];

        var date = new Date(time*1000)
        // var date = new Date;

        Date.prototype.customFormat = function(formatString){
            var YYYY,YY,MMMM,MMM,MM,M,DDDD,DDD,DD,D,hhhh,hhh,hh,h,mm,m,ss,s,ampm,AMPM,dMod,th;
            YY = ((YYYY=this.getFullYear())+"").slice(-2);
            MM = (M=this.getMonth()+1)<10?('0'+M):M;
            MMM = (MMMM=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][M-1]).substring(0,3);
            DD = (D=this.getDate())<10?(D):D;
            DDD = (DDDD=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"][this.getDay()]).substring(0,3);
            th=(D>=10&&D<=20)?'th':((dMod=D%10)==1)?'st':(dMod==2)?'nd':(dMod==3)?'rd':'th';
            formatString = formatString.replace("#YYYY#",YYYY).replace("#YY#",YY).replace("#MMMM#",MMMM).replace("#MMM#",MMM).replace("#MM#",MM).replace("#M#",M).replace("#DDDD#",DDDD).replace("#DDD#",DDD).replace("#DD#",DD).replace("#D#",D).replace("#th#",th);
            h=(hhh=this.getHours());
            if (h==0) h=24;
            if (h>12) h-=12;
            hh = h<10?('0'+h):h;
            hhhh = h<10?('0'+hhh):hhh;
            AMPM=(ampm=hhh<12?'am':'pm').toUpperCase();
            mm=(m=this.getMinutes())<10?('0'+m):m;
            ss=(s=this.getSeconds())<10?('0'+s):s;
            return formatString.replace("#hhhh#",hhhh).replace("#hhh#",hhh).replace("#hh#",hh).replace("#h#",h).replace("#mm#",mm).replace("#m#",m).replace("#ss#",ss).replace("#s#",s).replace("#ampm#",ampm).replace("#AMPM#",AMPM);
        };

      var diff = (new Date() - new Date(time*1000)) / 1000;
      if (diff < 60) { return "Just now"; }
      if (diff < 86400) {
          var i = 0, unit;
          while (unit = units[i++]) {
            if (diff < unit.limit || !unit.limit){
              var diff =  Math.floor(diff / unit.in_seconds);
              return diff + unit.name + (diff>1 ? "s ago" : " ago");
            }
          };
      }
      return date.customFormat( "#MMM# #DD##th#");
      // if (diff < 31556926) {
      //   return date.customFormat( "#MMM# #DD##th#");
      // }
      // return date.customFormat( "#YYYY#");
    });


    Handlebars.registerHelper ('timeAgo', function (time) {
      var units = [
        { name: "second", limit: 60, in_seconds: 1 },
        { name: "min", limit: 3600, in_seconds: 60 },
        { name: "hour", limit: 86400, in_seconds: 3600  },
        { name: "day", limit: 604800, in_seconds: 86400 },
        { name: "week", limit: 2629743, in_seconds: 604800  },
        { name: "month", limit: 31556926, in_seconds: 2629743 },
        { name: "year", limit: null, in_seconds: 31556926 }
      ];
      var diff = (new Date() - new Date(time*1000)) / 1000;
      if (diff < 5) { return "Just now"; }
      var i = 0, unit;
      while (unit = units[i++]) {
        if (diff < unit.limit || !unit.limit){
          var diff =  Math.floor(diff / unit.in_seconds);
          return diff + " " + unit.name + (diff>1 ? "s ago" : " ago");
        }
      };
    });
    
    Handlebars.registerHelper('StaticUrl', function() {
        return suiteio.staticUrl;
    });

    Handlebars.registerHelper('include', function(options) {
        var context = {},
            mergeContext = function(obj) {
                for(var k in obj)context[k]=obj[k];
            };
        mergeContext(this);
        mergeContext(options.hash);
        return options.fn(context);
    });

    Handlebars.registerHelper('random1toN', function(n) {
        var val = parseInt(Math.random() * n, 10) + 1;
        return val;
    });

});