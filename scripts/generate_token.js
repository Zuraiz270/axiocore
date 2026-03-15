const jwt = require('jsonwebtoken');

const secret = process.env.JWT_SECRET || 'dev-secret-do-not-use-in-prod';
const payload = {
  sub: 'user-1234',
  tenant_id: '123e4567-e89b-12d3-a456-426614174000',
};

const token = jwt.sign(payload, secret, { expiresIn: '1h' });
console.log(token);
