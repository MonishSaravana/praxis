// praxis.monishsaravana.com: HTTP basic auth (any username, one shared password), then serve index.html for directory
// paths and add the trailing slash to directory URLs so relative links inside /viewer/ and /studio/ resolve.
// The password is stored as a SHA-256 hash; __PWD_SHA256__ is filled in when the function is deployed, so the
// hash is not committed. See tools/site-auth.sh.
var crypto = require('crypto');
var PWD_SHA256 = '__PWD_SHA256__';

function unauthorized() {
  return {
    statusCode: 401,
    statusDescription: 'Unauthorized',
    headers: {
      'www-authenticate': { value: 'Basic realm="Praxis", charset="UTF-8"' },
      'cache-control': { value: 'no-store' }
    }
  };
}

function authorized(headers) {
  var h = headers.authorization;
  if (!h || h.value.slice(0, 6) !== 'Basic ') return false;
  var decoded = Buffer.from(h.value.slice(6), 'base64').toString();
  var pwd = decoded.slice(decoded.indexOf(':') + 1);
  return crypto.createHash('sha256').update(pwd).digest('hex') === PWD_SHA256;
}

function handler(event) {
  var r = event.request;
  if (!authorized(r.headers)) return unauthorized();
  var last = r.uri.split('/').pop();
  if (r.uri.charAt(r.uri.length - 1) === '/') {
    r.uri += 'index.html';
  } else if (last.indexOf('.') === -1) {
    return { statusCode: 301, statusDescription: 'Moved Permanently', headers: { location: { value: r.uri + '/' } } };
  }
  return r;
}
