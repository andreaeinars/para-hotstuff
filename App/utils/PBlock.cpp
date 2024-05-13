#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <string>
#include <cstring>

#include "PBlock.h"

void PBlock::serialize(salticidae::DataStream &data) const {
  data << this->set << this->prevHash << this->size << this->seqNumber;
  for (int i = 0; i < MAX_NUM_TRANSACTIONS; i++) {
    data << this->transactions[i];
  }
}

void PBlock::unserialize(salticidae::DataStream &data) {
  data >> this->set >> this->prevHash >> this->size >> this->seqNumber;
  for (int i = 0; i < MAX_NUM_TRANSACTIONS; i++) {
    data >> this->transactions[i];
  }
}

std::string PBlock::transactions2string() {
  std::string s;
  for (int i = 0; i < this->size; i++) {
    s += this->transactions[i].toString();
  }
  return s;
}

std::string PBlock::toString() {
  std::string text = std::to_string(this->set)
    + this->prevHash.toString()
    + std::to_string(this->seqNumber)
    + std::to_string(this->size)
    + transactions2string();
  return text;
}

std::string PBlock::prettyPrint() {
  std::string text = "";
  for (int i = 0; i < MAX_NUM_TRANSACTIONS && i < this->size; i++) {
    text += this->transactions[i].prettyPrint();
  }
  return ("PBLOCK[" + std::to_string(this->set)
          + "," + this->prevHash.prettyPrint()
          + "," + std::to_string(this->seqNumber)
          + "," + std::to_string(this->size)
          + ",{" + text + "}]");
}

Hash PBlock::hash() {
  unsigned char h[SHA256_DIGEST_LENGTH];
  std::string text = toString();

  if (!SHA256 ((const unsigned char *)text.c_str(), text.size(), h)){
    std::cout << KCYN << "SHA1 failed" << KNRM << std::endl;
    exit(0);
  }
  return Hash(h);
}

// checks whether this block extends the argument
bool PBlock::extends(Hash h) {
  return (this->prevHash == h);
}

bool PBlock::isDummy() { return !this->set; }
unsigned int PBlock::getSize() { return this->size; }
unsigned int PBlock::getSeqNumber() { return this->seqNumber; }
Transaction *PBlock::getTransactions() { return this->transactions; }

PBlock::PBlock(bool b) {
  this->prevHash=Hash();
  this->set=b;
}

PBlock::PBlock() {
  this->prevHash=Hash();
  this->set=true;
}

PBlock::PBlock(Hash prevHash, unsigned int size, unsigned int seqNumber,Transaction transactions[MAX_NUM_TRANSACTIONS]) {
  this->set=true;
  this->prevHash=prevHash;
  this->size=size;
  this->seqNumber=seqNumber;
  for (int i = 0; i < MAX_NUM_TRANSACTIONS; i++) {
    this->transactions[i]=transactions[i];
  }
}

bool PBlock::operator==(const PBlock& s) const {
  if (this->set != s.set || !(this->prevHash ==  s.prevHash) || this->size != s.size || this->seqNumber != s.seqNumber) { return false; }
  for (int i = 0; i < MAX_NUM_TRANSACTIONS && i < this->size; i++) { if (!(transactions[i] == s.transactions[i])) { return false; } }
  return true;
}
