from lambda_function import lambda_handler
from urllib.parse import unquote, parse_qsl

event = {
	"body-json" : "appIDs%5B%5D=asdfasf&paths%5B%5D=12&patterns%5B%5D=12&comments%5B%5D=1212&exclude%5B%5D=on&paths%5B%5D=12&patterns%5B%5D=12&comments%5B%5D=12&exclude%5B%5D=",
	"context" : {
		"resource-path" : ".well-known/apple-app-site-association",
		"http-method" : "POST"
	},
	"requestContext" : {
		"domainName" : "testmeout.binshare.co"
	}
}

lambda_handler(event, {})