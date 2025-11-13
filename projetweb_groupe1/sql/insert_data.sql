
INSERT INTO etat (id_status, description) VALUES
(0, 'Under way using engine'),
(1, 'At anchor'),
(2, 'Not under command'),
(3, 'Restricted manoeuverability'),
(4, 'Constrained by her draught'),
(5, 'Moored'),
(6, 'Aground'),
(7, 'Engaged in fishing'),
(8, 'Under way sailing'),
(9, 'Reserved for future amendment of Navigational Status for HSC'),
(10, 'Reserved for future amendment of Navigational Status for WIG'),
(11, 'Reserved for future use'),
(12, 'Reserved for future use'),
(13, 'Reserved for future use'),
(14, 'AIS-SART (active search and rescue transponder)'),
(15, 'Not defined (default)');

INSERT INTO navire (mmsi, name, length, width, draft, vtype, cargo) VALUES
(123456789, 'Test Ship 1', 100.0, 20.0, 5.0, 60, 60),
(987654321, 'Test Ship 2', 150.0, 25.0, 6.0, 70, 70),
(112233445, 'Test Ship 3', 80.0, 15.0, 4.0, 80, 80);

INSERT INTO pos (lon, lat, time, sog, cog, heading, mmsi, id_status) VALUES
(12.34567, 34.56789, '2023-10-01 12:00:00', 10.0, 180.0, 180.0, 123456789, 0),
(23.45678, 45.67890, '2023-10-01 12:05:00', 0.0, 0.0, 0.0, 987654321, 1),
(-12.34567, -34.56789, '2023-10-01 12:10:00', 5.0, 90.0, 90.0, 112233445, 2);

