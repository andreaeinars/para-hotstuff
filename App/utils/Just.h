#ifndef JUST_H
#define JUST_H


#include "Signs.h"
#include "RData.h"
#include "RDataPara.h"

#include "salticidae/stream.h"

enum class RDataType { RData, RDataPara };


class Just {
 private:
  bool set = false;
  Signs signs; // signature

  RDataType type;
  union {
    RData rdata;
    RDataPara rdataPara;
  };

 public:
  Just();
  Just(RDataType type);
  Just(RData rdata, Sign sign);
  Just(RDataPara rdata, Sign sign);
  Just(RData rdata, Signs signs);
  Just(RDataPara rdata, Signs signs);
  Just(bool b, RData rdata, Signs signs);
  Just(bool b, RDataPara rdata, Signs signs);

  ~Just();

  bool  isSet();
  RData getRData();
  RDataPara getRDataPara();
  Signs getSigns();
  RDataType getRDataType();

  void serialize(salticidae::DataStream &data) const;
  void unserialize(salticidae::DataStream &data);

  std::string prettyPrint();
  std::string toString();

  bool wellFormedInit();
  bool wellFormedNv();
  bool wellFormedPrep(unsigned int qsize);
  bool wellFormed(unsigned int qsize);
  View getCView();
  Hash getCHash();

  bool operator==(const Just& other) const;
};


#endif
