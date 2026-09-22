-- The SRP Irrigation schedule page has an address search feature. It will not
-- search for addresses shorter than 3 characters. There for, assume any
-- addresses this short are not valid.
select * from address where length(address) < 3;

-- There was one short address with a value of ','. Obviusly not a real
-- address.
delete from address where length(address) < 3;
