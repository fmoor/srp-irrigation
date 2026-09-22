load spatial;

select
    StreetNumb || ' ' || StreetDir || ' ' || StreetName || ' ' || StreetType
from parcel
where
    StreetNumb is not null
    and StreetName is not null
    and StreetDir is not null
    and StreetType is not null
limit 10;
