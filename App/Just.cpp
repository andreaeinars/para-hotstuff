#include "Just.h"

Just::Just() : set(false), type(RDataType::RData), rdata() {}

Just::Just(RDataType type) : set(false), type(type) {
    if (type == RDataType::RData) {
        rdata = RData();  // Initialize with default RData
    } else if (type == RDataType::RDataPara) {
        rdataPara = RDataPara();  // Initialize with default RDataPara
    }
}

Just::Just(RData rdata, Sign sign) {
  this->set = true;
  this->type = RDataType::RData;
  this->rdata = rdata;
  this->signs = Signs(sign);
}

Just::Just(RDataPara rdata, Sign sign) {
  this->set = true;
  this->type = RDataType::RDataPara;
  this->rdataPara = rdata;
  this->signs = Signs(sign);
}

Just::Just(RData rdata, Signs signs) {
  this->set = true;
  this->type = RDataType::RData;
  this->rdata = rdata;
  this->signs = signs;
}

Just::Just(RDataPara rdata, Signs signs) {
  this->set = true;
  this->type = RDataType::RDataPara;
  this->rdataPara = rdata;
  this->signs = signs;
}

Just::Just(bool b, RData rdata, Signs signs) {
  this->set = b;
  this->type = RDataType::RData;
  this->rdata = rdata;
  this->signs = signs;
}

Just::Just(bool b, RDataPara rdata, Signs signs) {
  this->set = b;
  this->type = RDataType::RDataPara;
  this->rdataPara = rdata;
  this->signs = signs;
}

Just::~Just() {
  if (type == RDataType::RDataPara) {
    rdataPara.~RDataPara();
  } else {
    rdata.~RData();
  }
}

bool  Just::isSet()    { return this->set;   }

RData Just::getRData() {
  if (this->type == RDataType::RData) {
    return this->rdata;
  }
  throw std::runtime_error("Incorrect type, expected RData");
}

RDataPara Just::getRDataPara() {
  if (this->type == RDataType::RDataPara) {
    return this->rdataPara;
  }
  throw std::runtime_error("Incorrect type, expected RDataPara");
}

Signs Just::getSigns() { return this->signs; }

RDataType Just::getRDataType() { return this->type; }

void Just::serialize(salticidae::DataStream &data) const {
  data << this->set;
  data << static_cast<int>(this->type);
  if (this->type == RDataType::RData) {
    this->rdata.serialize(data);
  } else if (this->type == RDataType::RDataPara) {
    this->rdataPara.serialize(data);
  }
  data << this->signs;
}

void Just::unserialize(salticidae::DataStream &data) {
  data >> this->set;
  int typeInt;
  data >> typeInt;
  this->type = static_cast<RDataType>(typeInt);
  if (this->type == RDataType::RData) {
    this->rdata.unserialize(data);
  } else if (this->type == RDataType::RDataPara) {
    this->rdataPara.unserialize(data);
  }
  data >> this->signs;
}

std::string Just::prettyPrint() {
  return "JUST[" + std::to_string(this->set) + "," +
         (this->type == RDataType::RData ? this->rdata.prettyPrint() : this->rdataPara.prettyPrint()) +
         "," + this->signs.prettyPrint() + "]";
}

std::string Just::toString() {
  return std::to_string(this->set) +
         (this->type == RDataType::RData ? this->rdata.toString() : this->rdataPara.toString()) +
         this->signs.toString();
}

bool Just::wellFormedInit() {
  return (this->type == RDataType::RData &&
          this->rdata.getPropv() == 0 &&
          this->rdata.getJustv() == 0 &&
          this->rdata.getPhase() == PH1_NEWVIEW &&
          this->signs.getSize() == 0);
}

bool Just::wellFormedNv() {
  return (this->rdata.getJusth().getSet() &&
          this->rdata.getPhase() == PH1_NEWVIEW &&
          this->signs.getSize() == 1);
}

bool Just::wellFormedPrep(unsigned int qsize) {
  return (this->rdata.getProph().getSet() &&
          this->rdata.getPhase() == PH1_PREPARE &&
          this->signs.getSize() == qsize);
}

bool Just::wellFormed(unsigned int qsize) {
  return (wellFormedInit() || wellFormedNv() || wellFormedPrep(qsize));
}

View Just::getCView() {
  if (wellFormedInit() || wellFormedNv()) {
    return this->rdata.getJustv();
  }
  return this->rdata.getPropv();
}

Hash Just::getCHash() {
  if (wellFormedInit() || wellFormedNv()) {
    return this->rdata.getJusth();
  }
  return this->rdata.getProph();
}

bool Just::operator==(const Just &other) const {
    if (this->set != other.set) return false;
    if (this->type != other.type) return false;
    if (this->signs == other.signs){
      if (this->type == RDataType::RData) {
          return this->rdata == other.rdata;
      } else {
          return this->rdataPara == other.rdataPara;
      }
      return true;  
    }
}