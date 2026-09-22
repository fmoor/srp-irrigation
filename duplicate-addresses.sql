-- Are there any duplicate addresses in this data set?
with duplicate as (
    select
        address
    from address
    group by address
        having count(address) > 1
)
select a.*
from address as a
join duplicate as d on d.address = a.address
order by a.address
;

-- It turns out that there are 25 addresses that have more than are associated
-- with more than one account. This is note meaningful for this project. The
-- duplicates can be dropped.
delete from address
where id not in (
    select min(id)
    from address
    group by address
        having count(address) > 1
)
;
