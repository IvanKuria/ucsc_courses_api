from src.config import ConfigObject
import requests
from src.helper import Helpers

class CourseParser():
    # Parses the latest term info from the front page
    @staticmethod
    def get_term_info():
        #Gets the raw HTML results
        raw_html_results = requests.get(ConfigObject.api_endpoint).text

        # Replacement 1: Get rid of all new lines
        # Replacement 2: Every HTML comment will have a newline before it to make parsing easier
        parsed_results = str(raw_html_results.replace('\n','').replace('<!--','\n<!-- ')).split('\n')[4:]

        # Grab the string containing all the terms
        term_string = ""
        for entries in parsed_results:
            if 'term_dropdown' in entries:
                term_string = entries

        # Yes I realize that I could do this within the for loop to save runtime complexity..
        # but this is easier to read/understand for the laymen

        term_string = term_string.replace('<option value','\n<option value').split('\n')[1:]
        term_array = []

        for term in term_string:
            # Edge case: the first one has a different html tag than the rest, so we accomodate
            if 'selected' in term:
                term_id = Helpers.find_between(Helpers, term, '<option value = "', '"')
                term_value = Helpers.find_between(Helpers, term, '{}" selected="selected">'.format(term_id), '</option')
            else:
                term_id = Helpers.find_between(Helpers, term, '<option value = "', '"')
                term_value = Helpers.find_between(Helpers, term, '{}" >'.format(term_id), '</option')
            term_array.append(
                {
                    "term_id": term_id,
                    "term_value": term_value
                }
            )

        return term_array

    @staticmethod
    def parse_request(request):
        # See: https://stackoverflow.com/a/46321103 for reading uri queries and assigning default values
        action = request.args.get('ACTION', default="results", type=str)
        acad_career = request.args.get('acad_career', default='', type=str)
        catalog_nbr_op = request.args.get('catalog_nbr_op', default='=', type=str)
        catalog_nbr = request.args.get('catalog_nbr', default='', type=str)
        crse_units_exact = request.args.get('crse_units_exact', default='', type=str)
        crse_units_from = request.args.get('crse_units_from', default='', type=str)
        crse_units_op = request.args.get('crse_units_op', default='=', type=str)
        crse_units_to = request.args.get('crse_units_to', default='', type=str)
        days = request.args.get('days', default='', type=str)
        ge = request.args.get('ge', default='', type=str)
        instr_name_op = request.args.get('instr_name_op', default='=', type=str)
        instructor = request.args.get('instructor', default='', type=str)
        reg_status = request.args.get('reg_status', default='O', type=str)
        if reg_status == 'open': reg_status = 'O'
        elif reg_status == 'closed': reg_status = 'C'
        subject = request.args.get('subject', default='', type=str)
        term = request.args.get('term', default=CourseParser.get_term_info()[0].get('term_id'), type=str)
        times = request.args.get('times', default='', type=str)
        title = request.args.get('title', default='', type=str)

        return {
            "action": action,
            "binds[:acad_career]": acad_career,
            "binds[:catalog_nbr_op]": catalog_nbr_op,
            "binds[:catalog_nbr]": catalog_nbr,
            "binds[:crse_units_exact]": crse_units_exact,
            "binds[:crse_units_from]": crse_units_from,
            "binds[:crse_units_op]": crse_units_op,
            "binds[:crse_units_to]": crse_units_to,
            "binds[:days]": days,
            "binds[:ge]": ge,
            "binds[:instr_name_op]": instr_name_op,
            "binds[:instructor]": instructor,
            "binds[:reg_status]": reg_status,
            "binds[:subject]": subject.upper(),
            "binds[:term]": term,
            "binds[:times]": times,
            "binds[:title]": title,
            "rec_dur":int(request.args.get('count', 1000))
        }

    @staticmethod
    def parse_classes_page(payload):
        if 'type' in payload:
            course_type =payload['type']
            if course_type == 'lower':
                payload["binds[:catalog_nbr_op]"] = '<'
                payload["binds[:catalog_nbr]"] = '100'
            elif course_type == 'upper':
                payload["binds[:catalog_nbr_op]"] = '>'
                payload["binds[:catalog_nbr]"] = '99'
            elif course_type == 'undergrad':
                payload["binds[:catalog_nbr_op]"] = '<'
                payload["binds[:catalog_nbr]"] = '200'
            elif course_type == 'grade':
                payload["binds[:catalog_nbr_op]"] = '>'
                payload["binds[:catalog_nbr]"] =  '199'
            else:
                payload["binds[:catalog_nbr_op]"] = '='
                payload["binds[:catalog_nbr]"] = ''
            del payload['type']
        # Grabs the raw HTML page from the endpoint
        raw_html_results = requests.post(ConfigObject.api_endpoint,data=payload).text

        # Replacement 1: Get rid of all new lines
        # Notes : I saw that "panel-heading.*" are the only differentiators when parsing through the results
        # Replacement 2: Every panel-heading piece will have a newline, for easier parsing
        # Split the results by the newline that were given, and skip the first line
        parsed_results = str(raw_html_results.replace("\n","").replace\
            ('<div class="panel-heading panel-heading-custom">',
             '\n<div class="panel-heading panel-heading-custom">')).replace('<br>',' ').split("\n")[1:]


        return_data = []
        for entries in parsed_results:
            if not entries.strip():
                continue
                
            # Grab relevant data, heavily relying on html elements ( this may change a lot as the HTML page changes )
            # Updated for 2025 HTML structure
            filtered_entry = Helpers.find_between(Helpers,entries,'<div class="panel-heading panel-heading-custom"><H2 style="margin:0px;">', '</H2></div>')
            if not filtered_entry:
                continue
                
            filtered_json = {}
            print(f'filtered html entry: {filtered_entry}')
            
            # Extract course information from the new HTML structure
            descriptive_link = Helpers.find_between(Helpers, filtered_entry, 'href = "index.php?', '"')
            class_name = Helpers.find_between(Helpers, filtered_entry, '{}">'.format(descriptive_link), '</a>')
            title = Helpers.find_between(Helpers, filtered_entry, 'title="', '"')
            link_sources = Helpers.find_between(Helpers,filtered_entry,'<img src="','"')
            class_id = Helpers.find_between(Helpers,filtered_entry,'<a id="','"').replace('class_id_','')
            
            # Look for the panel-body section for additional course details
            panel_body_start = entries.find('<div class="panel-body"')
            if panel_body_start != -1:
                panel_body = entries[panel_body_start:panel_body_start + 2000]  # Get enough content
                
                # Extract instructor (look for fa-user icon)
                instructor_match = Helpers.find_between(Helpers, panel_body, '<i class="fa fa-user"', '</div>')
                if instructor_match:
                    instructor = instructor_match.split('>')[-1].strip()
                else:
                    instructor = "Staff"
                
                # Extract location (look for fa-location-arrow icon)
                location_match = Helpers.find_between(Helpers, panel_body, '<i class="fa fa-location-arrow"', '</div>')
                if location_match:
                    location = location_match.split('>')[-1].strip()
                else:
                    location = "TBA"
                
                # Extract date/time (look for fa-clock-o icon)
                datetime_match = Helpers.find_between(Helpers, panel_body, '<i class="fa fa-clock-o"', '</div>')
                if datetime_match:
                    date_time = datetime_match.split('>')[-1].strip()
                else:
                    date_time = "TBA"
                
                # Extract enrollment info
                enrolled_match = Helpers.find_between(Helpers, panel_body, 'Enrolled</div>', '</div>')
                if enrolled_match:
                    enrolled = enrolled_match.strip()
                else:
                    enrolled = "0 of 0"
            else:
                instructor = "Staff"
                location = "TBA"
                date_time = "TBA"
                enrolled = "0 of 0"
            
            # Parse into JSON document
            filtered_json['status'] = title if title else "Open"
            filtered_json['link_sources'] = link_sources
            filtered_json['class_id'] = class_id
            filtered_json['descriptive_link'] = descriptive_link
            filtered_json['class_name'] = class_name.replace('&nbsp;',' ') if class_name else "Unknown Course"
            filtered_json['instructor'] = instructor
            filtered_json['location'] = location
            filtered_json['date_time'] = date_time
            filtered_json['enrolled'] = enrolled
            return_data.append(filtered_json)


        return return_data