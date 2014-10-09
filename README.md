https://help.github.com/articles/github-flavored-markdown

# Microput 

Microput is a product/offering/module that allows a user to create a URL capturing some set of data and specify recurring reports that are to be run on this.

It allows one to:

- Specify what data to capture
- Specify what the URLs return

## Architecture

### Metadata DB

Metadata is stored in MySQL. It drives the UI to allow a user to select only things that make sense at the moment.

#### Concepts

##### Data collection

A data collection is a URL that collects data. It has:

1. A payload (that is, what is being returned from the URL).
2. Attributes

##### Payload

Payload has the following properties:



### UI

### Data capture and response

Data capture and payload return is done via NGINX configuration (with Lua). Data is written to log files, and then on schedule pushed to Amazon S3 (upload.py), partitioned in two ways:

The following directory structure is assumed (this repository contains part of it):

The re-configuration of the NGINX config files is done on schedule by two processes:

- create_stat_bundle.py 

The user specifies a set of columns, and a flag, specifying whether to capture the value of this column. This is because a column can be present for the purpose of using it in the Return Payload (see below), but does not need to be captured for reporting. Each column can be one of the following types
Predefined macros

One of a set of pre-defined macros, such as:

    $remote_addr -- IP address of the user

List of currently available macros (with their descriptions) is to be looked up in the DB. 
Query parameters

These can be arbitrary (when stored, they will have $arg_ prefix, such as $arg_foo). User can supply these, and these will become part of the URL.
Cookies

These also can be arbitrary and will correspond to the cookies. Addressed as $cookie_opendsp_xyz.
HTTP headers

These have prefix $http_ and the rest of the string is a lower-case HTTP header name, with dashes converted to underscore (e.g., $http_user_agent). Obviously, given the fact that user-defined X- headers are possible, these can take any value. However:

    UI should present this as a list of standard HTTP headers (looked up in the DB), with an option to create a custom one
    The custom one can only start with X-

The UI should present the headers as User-Agent, Content-Type, etc, while saving the values as $http_user_agent, $content_type, etc.
Geo lookup

These have prefix $geo and are limited to a set specified in the data
model (therefore the UI should present this choice in a dropdown).
Cookie-setting behavior
Setting

A user may specify that certain cookies are set during the hit of this URL. She specifies the cookie names, expiration (in days?), and values. Macros from the above list may be used in the values. Cookie domain is always opendsp.com. 
Unsetting

A user may specify that certain cookies are unset during the hit of this URL. She specifies the cookie names, and expiration (in days?). 
Return payload

Return payload can be one of the following
Pixel

A 200 HTTP return code with a 1x1 GIF.
Redirect

The user specifies:

    Which of the 3xx HTTP return codes to return (enforced by application and/or data model to only be a 3xx code.
    The URL to redirect to. Macros from the above list may be used in the URL.

Arbitrary payload

The user specifies

* Return Content-type
* Payload as text. Macros from the above list may be used inside the text.
Architecture
Data definition

The data model is as follows:
Data collection

