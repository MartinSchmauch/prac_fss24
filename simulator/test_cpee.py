import json
import bottle

@bottle.route('/test_dict', method='POST')
def test_dict():
    sample_dict = {"cid": "1", "diagnosis": "A"}
    response_content = json.dumps({"state": sample_dict})

    return bottle.HTTPResponse(
        response_content,
        status=200,
        headers = { 'content-type': 'application/json'}
        )
    
@bottle.route('/read_x', method='POST')


if __name__ == '__main__':
    bottle.run(host='::0', port=12790)
    
    # instance 71392