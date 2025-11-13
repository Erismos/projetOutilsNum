#------------------------------------------------------------
#        Script MySQL.
#------------------------------------------------------------

DROP TABLE IF EXISTS navire;
DROP TABLE IF EXISTS etat;
DROP TABLE IF EXISTS pos;

#------------------------------------------------------------
# Table: navire
#------------------------------------------------------------

CREATE TABLE navire(
        mmsi   Int NOT NULL ,
        name   Varchar (50) NOT NULL ,
        length Float NOT NULL ,
        width  Float NOT NULL ,
        draft  Float NOT NULL ,
        cargo  Int NOT NULL   ,
        vtype  Int
	,CONSTRAINT navire_PK PRIMARY KEY (mmsi)
)ENGINE=InnoDB;


#------------------------------------------------------------
# Table: etat
#------------------------------------------------------------

CREATE TABLE etat(
        id_status   Int NOT NULL ,
        description Varchar (80) NOT NULL
	,CONSTRAINT etat_PK PRIMARY KEY (id_status)
)ENGINE=InnoDB;


#------------------------------------------------------------
# Table: pos
#------------------------------------------------------------

CREATE TABLE pos(
        id_pos      Int NOT NULL AUTO_INCREMENT,
        lon         Float NOT NULL ,
        lat         Float NOT NULL ,
        time        Datetime NOT NULL ,
        sog         Float NOT NULL ,
        cog         Float NOT NULL ,
        heading     Float NOT NULL ,
        mmsi        Int NOT NULL ,
        id_status   Int NOT NULL
	,CONSTRAINT pos_PK PRIMARY KEY (id_pos)

	,CONSTRAINT pos_navire_FK FOREIGN KEY (mmsi) REFERENCES navire(mmsi)
	,CONSTRAINT pos_etat0_FK FOREIGN KEY (id_status) REFERENCES etat(id_status)
)ENGINE=InnoDB;