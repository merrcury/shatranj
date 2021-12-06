# INSTALL OPENZEPPELIN WITH npm
npm install @openzeppelin/contracts

# CREATE SOLIDITY SMART CONTRACT, COMPILE & DEPLOY
```Bash
vim ashf.sol

npx truffle compile

npx truffle develop

const myToken = await ExampleToken.new()

(await myToken.totalSupply()).toString()|
'10000000000000000000000'

myToken.transfer(...)|
```

# SAMPLE EXAMPLE.sol
```Solidity
pragma solidity ^0.8.0;
import "@openzeppelin/contracts/token/ERC20/
ERC20.sol";
contract ExampleToken is ERC20 {
constructor ()
ERC20("ExampleToken", "EGT")
{
_mint(
msg.sender, 10000 * 10 ** decimals()
);
}
}


```

 
 