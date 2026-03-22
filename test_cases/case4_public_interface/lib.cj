// 测试用例4: public接口竞争
// 两个public函数访问同一共享变量

// 全局共享变量
public var sharedData: Int64 = 0

// public函数1: 写入
public func updateData(newValue: Int64) {
    sharedData = newValue  // 写操作，第8行
}

// public函数2: 读取
public func readData(): Int64 {
    return sharedData  // 读操作，第13行
}