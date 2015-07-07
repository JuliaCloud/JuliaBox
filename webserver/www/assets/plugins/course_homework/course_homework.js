var CourseHomework = (function($, _, undefined){
	var self = {
        hw_check: function(course, problemset, question, answer, record, s, f) {
            if(!s) {
                s = function(status){
                    if(status.code == 0) {
                        bootbox.dialog({
                            message: JuliaBox._json_to_table(status.data),
                            title: 'Evaluation'
                        }).find("div.modal-dialog").addClass("bootbox70");
                    }
                    else {
                        bootbox.alert('<pre>' + status.data + '</pre>');
                    }
                };
            };
            if(!f) {
	    	    f = function() { bootbox.alert("Oops. Unexpected error while verifying answer.<br/><br/>Please try again later."); };
            };
            mode = record ? "submit" : "check";
            JuliaBox.comm('/jboxplugin/hw/', 'POST', {
                'mode': mode,
                'params': JSON.stringify({
                    'course': course,
                    'problemset': problemset,
                    'question': question,
                    'answer': answer
                })
            },
            s, f);
        },

        hw_myreport: function(course, problemset, questions, s, f) {
            self.hw_report_base("myreport", course, problemset, questions, s, f);
        },

        hw_report: function(course, problemset, questions, s, f) {
            self.hw_report_base("report", course, problemset, questions, s, f);
        },

        hw_report_base: function(apiname, course, problemset, questions, s, f) {
            if(!s) {
                s = function(report){
                    if(report.code == 0) {
                        bootbox.dialog({
                            message: JuliaBox._json_to_table(report.data),
                            title: 'Evaluations'
                        }).find("div.modal-dialog").addClass("bootbox70");
                    }
                    else {
                        bootbox.alert('<pre>' + report.data + '</pre>');
                    }
                };
            };
            if(!f) {
	    	    f = function() { bootbox.alert("Oops. Unexpected error while retrieving evaluations.<br/><br/>Please try again later."); };
            };
            params = {
                'course': course,
                'problemset': problemset
            }
            if(questions) {
                params['questions'] = questions;
            }

            JuliaBox.comm('/jboxplugin/hw/', 'POST', {
                'mode': apiname,
                'params': JSON.stringify(params)
            },
            s, f);
        },

        hw_metadata: function(course, problemset, questions, s, f) {
            if(!s) {
                s = function(ans){
                    if(ans.code == 0) {
                        bootbox.dialog({
                            message: JuliaBox._json_to_table(ans.data),
                            title: 'Answers'
                        }).find("div.modal-dialog").addClass("bootbox70");
                    }
                    else {
                        bootbox.alert('<pre>' + ans.data + '</pre>');
                    }
                };
            };
            if(!f) {
	    	    f = function() { bootbox.alert("Oops. Unexpected error while retrieving answers.<br/><br/>Please try again later."); };
            };
            params = {
                'course': course,
                'problemset': problemset
            }
            if(questions) {
                params['questions'] = questions;
            }
            JuliaBox.comm('/jboxplugin/hw/', 'POST', {
                'mode': 'metadata',
                'params': JSON.stringify(params)
            },
            s, f);
        },

        hw_create: function(course, s, f) {
            if(!s) {
                s = function(result){
                    if(result.code == 0) {
                        bootbox.dialog({
                            message: JuliaBox._json_to_table(result.data),
                            title: 'Create Course'
                        }).find("div.modal-dialog").addClass("bootbox70");
                    }
                    else {
                        bootbox.alert('<pre>' + result.data + '</pre>');
                    }
                };
            };
            if(!f) {
	    	    f = function() { bootbox.alert("Oops. Unexpected error while creating course.<br/><br/>Please try again later."); };
            };
            JuliaBox.comm('/jboxplugin/hw/', 'POST', {
                'mode': 'create',
                'params': JSON.stringify(course)
            },
            s, f);
        }
	};
	return self;
})(jQuery, _);