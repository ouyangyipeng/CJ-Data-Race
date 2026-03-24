// 测试用例12: 函数调用中的数据竞争
// 通过函数调用访问共享变量

var globalCounter: Int64 = 0

func increment() {
    globalCounter = globalCounter + 1
}

func readCounter(): Int64 {
    return globalCounter
}

main() {
    // 线程1: 调用increment写
    spawn {
        increment()
    }
    
    // 线程2: 调用readCounter读
    spawn {
        let value = readCounter()
        println(value)
    }
    
    println(globalCounter)
}