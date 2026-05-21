```sql
  -- First, delete agent_messages for users who have no messages
DELETE FROM agent_messages
  WHERE user_id IN (
      SELECT u.id
      FROM users u
      LEFT JOIN messages m ON u.id = m.user_id
      WHERE m.user_id IS NULL
  );

 -- Then, delete users who have no messages
  DELETE FROM users
  WHERE id NOT IN (
      SELECT DISTINCT user_id
      FROM messages
      WHERE user_id IS NOT NULL
  );

 -- Update messages missing geo data using user geo data.
UPDATE messages m
  SET
      ip_address = u.ip_address,
      user_agent = u.user_agent,
      country = u.country,
      region = u.region,
      city = u.city
  FROM users u
  WHERE m.user_id = u.id
    AND (
      m.ip_address IS NULL
      OR m.country IS NULL
      OR m.region IS NULL
      OR m.city IS NULL
    )
    AND u.ip_address IS NOT NULL
    AND u.country IS NOT NULL;

```
